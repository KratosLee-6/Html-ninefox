//! Html九尾狐 桌面壳（v0.9.0 · Tauri 里程碑）
//!
//! 职责链（PLAN-v0.9 §二·五 sidecar 架构决策）：
//!   选空闲端口 → spawn PyInstaller sidecar（HtmlNineFox.exe --no-browser
//!   --strict-port）→ 轮询 /api/health 直到 200（verify_portable 纪律）→
//!   导航 webview 到工作台 → 退出时回收子进程。
//! 与 PyInstaller 便携包/安装包并存：壳是增量形态，不是替代。
//! sidecar 定位：环境变量 HTMLNINEFOX_SIDECAR > 主程序同目录 > sidecar/
//! 子目录 > 仓库开发路径（cargo tauri dev）。

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::Manager;

struct SidecarProcess(Mutex<Option<Child>>);

fn find_free_port() -> Option<u16> {
    TcpListener::bind("127.0.0.1:0")
        .ok()
        .and_then(|l| l.local_addr().ok())
        .map(|a| a.port())
}

fn sidecar_candidates() -> Vec<PathBuf> {
    let mut candidates = Vec::new();
    if let Ok(env_path) = std::env::var("HTMLNINEFOX_SIDECAR") {
        candidates.push(PathBuf::from(env_path));
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            // NSIS/便携布局：sidecar 与主程序同目录；onedir 整目录拷进
            // sidecar/ 子目录的布局各留一条候选。
            candidates.push(dir.join("HtmlNineFox.exe"));
            candidates.push(
                dir.join("sidecar")
                    .join("HtmlNineFox")
                    .join("HtmlNineFox.exe"),
            );
        }
    }
    // 开发/打包回退：build_portable.py 的 onedir 产物与 build_shell_bundle.py
    // 组装的捆绑布局（从仓库根或 src-tauri 运行时各留一条）。
    for base in [PathBuf::from("."), PathBuf::from("..")] {
        candidates.push(
            base.join("build")
                .join("windows")
                .join("dist")
                .join("HtmlNineFox")
                .join("HtmlNineFox.exe"),
        );
        candidates.push(
            base.join("sidecar")
                .join("HtmlNineFox")
                .join("HtmlNineFox.exe"),
        );
    }
    candidates
}

fn spawn_sidecar(port: u16) -> Result<Child, String> {
    let mut tried = Vec::new();
    for path in sidecar_candidates() {
        if !path.is_file() {
            tried.push(format!("{}（不存在）", path.display()));
            continue;
        }
        let child = Command::new(&path)
            .arg("--port")
            .arg(port.to_string())
            .arg("--strict-port")
            .arg("--no-browser")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("{} 启动失败：{e}", path.display()))?;
        return Ok(child);
    }
    Err(format!(
        "找不到 HtmlNineFox.exe（sidecar）。可设置环境变量 HTMLNINEFOX_SIDECAR 指向它。已尝试：{}",
        tried.join("；")
    ))
}

/// verify_portable 纪律的壳内版：真实 HTTP GET /api/health，见到 200 才算就绪。
fn wait_for_health(port: u16, deadline: Duration) -> bool {
    let started = Instant::now();
    let request = format!("GET /api/health HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n\r\n");
    while started.elapsed() < deadline {
        if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) {
            let _ = stream.write_all(request.as_bytes());
            let mut buffer = [0u8; 256];
            if let Ok(n) = stream.read(&mut buffer) {
                let head = String::from_utf8_lossy(&buffer[..n]);
                if head.starts_with("HTTP/1.0 200") || head.starts_with("HTTP/1.1 200") {
                    return true;
                }
            }
        }
        std::thread::sleep(Duration::from_millis(400));
    }
    false
}

fn loader_message(window: &tauri::WebviewWindow, message: &str) {
    let script = format!(
        "document.querySelector('h1').textContent = {};",
        serde_json::to_string(message).unwrap_or_else(|_| "\"…\"".into()),
    );
    let _ = window.eval(&script);
}

fn kill_sidecar(app: &tauri::AppHandle) {
    if let Some(state) = app.try_state::<SidecarProcess>() {
        if let Ok(mut guard) = state.0.lock() {
            if let Some(child) = guard.as_mut() {
                let _ = child.kill();
                let _ = child.wait();
            }
            *guard = None;
        }
    }
}

fn main() {
    let port = find_free_port().expect("找不到空闲端口");
    tauri::Builder::default()
        .manage(SidecarProcess(Mutex::new(None)))
        .setup(move |app| {
            let handle = app.handle().clone();
            let window = app.get_webview_window("main").ok_or("主窗口不存在")?;

            // 托盘：打开工作台 / 退出
            let open_item =
                tauri::menu::MenuItem::with_id(app, "open", "打开工作台", true, None::<&str>)?;
            let quit_item =
                tauri::menu::MenuItem::with_id(app, "quit", "退出 Html九尾狐", true, None::<&str>)?;
            let menu = tauri::menu::Menu::with_items(app, &[&open_item, &quit_item])?;
            let tray = tauri::tray::TrayIconBuilder::with_id("fox-tray")
                .tooltip("Html九尾狐 · 本地优先")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "open" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    "quit" => {
                        kill_sidecar(app);
                        app.exit(0);
                    }
                    _ => {}
                });
            let tray = match app.default_window_icon().cloned() {
                Some(icon) => tray.icon(icon),
                None => tray,
            };
            tray.build(app)?;

            // sidecar 生命周期：后台线程 spawn + 健康轮询 + 导航/报错
            std::thread::spawn(move || {
                let spawn_result = spawn_sidecar(port);
                let child = match spawn_result {
                    Ok(child) => child,
                    Err(message) => {
                        loader_message(&window, &message);
                        return;
                    }
                };
                if let Some(state) = handle.try_state::<SidecarProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        *guard = Some(child);
                    }
                }
                if wait_for_health(port, Duration::from_secs(45)) {
                    let _ = window.eval(&format!(
                        "window.location.replace('http://127.0.0.1:{port}/')",
                    ));
                } else {
                    loader_message(
                        &window,
                        "工作台启动超时（45 秒）。请查看托盘退出后重试，或改用便携包/安装包。",
                    );
                }
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            // 关窗 = 退出整个壳（托盘继续常驻的场景留给后续批次），先回收 sidecar
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                kill_sidecar(window.app_handle());
                window.app_handle().exit(0);
            }
        })
        .run(tauri::generate_context!())
        .expect("Html九尾狐 壳运行失败");
}
