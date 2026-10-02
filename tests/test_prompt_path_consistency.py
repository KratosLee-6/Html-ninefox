"""C4 gate: the analyze path and the generate path must build the same prompt.

Why this exists
---------------
`server/app.py::_Handler._prompt_and_inputs` and
`application.py::StudioApplication._prepare_generation` are two independent
implementations of the same rule: turn (prompt, input_ids) into the prompt
that is finally handed to the generators. Nothing asserts they agree, so the
layout the workbench shows after Analyze can quietly diverge from the layout
that Generate actually produces -- and nothing fails.

This file pins the invariant. It asserts, it does not refactor: the
duplicated bodies stay until somebody can see what merging them would cost.

Known differences deliberately NOT asserted here
------------------------------------------------
1. `str(item)` coercion on input ids exists only on the adapter side. It only
   matters for non-string ids arriving over HTTP; `GenerationRequest.input_ids`
   is typed `tuple[str, ...]`, and `InputStore.describe` already filters to
   32-hex ids. Asserting it would encode a difference rather than an invariant.
2. `prompt_required` is raised only by the application layer. The adapter has
   the equivalent check at the handler (`app.py::_api_analyze`), so asserting
   the raw function pair on empty input would produce a false positive.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from htmlninefox.application import GenerationRequest, StudioApplication
from htmlninefox.server.app import _Handler
from htmlninefox.server.inputs import InputStore

DEFAULT_ATTACHMENT_PROMPT = "请根据用户上传的附件生成合适的 HTML 作品"


class _AdapterStub:
    """Minimal stand-in for the HTTP handler: it only needs `_inputs()`."""

    def __init__(self, store: InputStore) -> None:
        self._store = store

    def _inputs(self) -> InputStore:
        return self._store


class _ApplicationStub:
    """Minimal stand-in for the application: it only needs `dependencies.inputs`."""

    def __init__(self, store: InputStore) -> None:
        self.dependencies = SimpleNamespace(inputs=store)


def _make_store(root: Path) -> InputStore:
    # InputStore.__init__ 会自己再拼一层 .inputs，所以 meta.json 必须落在
    # <root>/.inputs/<id>/ 下——少写这层 describe() 会静默返回空列表，
    # 表现为「仅附件」用例莫名抛 prompt_required。
    store = InputStore(root)
    folder = store.root / INPUT_ID
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "meta.json").write_text(
        json.dumps({
            "id": INPUT_ID,
            "name": "参考稿.md",
            "kind": "markdown",
            "mime": "text/markdown",
            "size": 42,
            "excerpt": "像素花园 排版参考",
        }, ensure_ascii=False), encoding="utf-8")
    return store


def _adapter(store: InputStore, body: dict) -> tuple[str, list[dict]]:
    return _Handler._prompt_and_inputs(_AdapterStub(store), body)


def _application(store: InputStore, prompt: str,
                 input_ids: tuple[str, ...]) -> tuple[str, list[dict]]:
    request = GenerationRequest(prompt=prompt, input_ids=input_ids)
    return StudioApplication._prepare_generation(_ApplicationStub(store), request)


INPUT_ID = "0123456789abcdef0123456789abcdef"
CASES = [    ("prompt only", "做一个极简落地页", ()),
    ("attachment only", "", (INPUT_ID,)),
    ("prompt and attachment", "按附件改写", (INPUT_ID,)),
    ("unknown attachment id", "按附件改写", ("ffffffffffffffffffffffffffffffff",)),
    ("whitespace prompt with attachment", "   ", (INPUT_ID,)),
]


def test_prompt_paths_agree_on_every_input_shape(tmp_path: Path) -> None:
    store = _make_store(tmp_path / "inputs")
    for label, prompt, input_ids in CASES:
        adapter_prompt, adapter_items = _adapter(
            store, {"prompt": prompt, "inputs": list(input_ids)})
        app_prompt, app_items = _application(store, prompt, input_ids)
        assert adapter_prompt == app_prompt, (
            f"[{label}] 两条路径产出的 prompt 不一致：\n"
            f"  analyze  ={adapter_prompt!r}\n"
            f"  generate ={app_prompt!r}")
        assert adapter_items == app_items, (
            f"[{label}] 两条路径产出的附件描述不一致：\n"
            f"  analyze  ={adapter_items!r}\n"
            f"  generate ={app_items!r}")


def test_attachment_only_input_yields_the_shared_default_prompt(tmp_path: Path) -> None:
    """仅附件时两侧必须落到同一条默认串——这条串目前字面量重复在两处。"""
    store = _make_store(tmp_path / "inputs")
    adapter_prompt, _ = _adapter(store, {"prompt": "", "inputs": [INPUT_ID]})
    app_prompt, _ = _application(store, "", (INPUT_ID,))
    assert DEFAULT_ATTACHMENT_PROMPT in adapter_prompt
    assert adapter_prompt == app_prompt
    assert app_prompt == adapter_prompt


def test_non_string_input_id_does_not_break_the_adapter_path(tmp_path: Path) -> None:
    """HTTP 可以送来非字符串 id；adapter 侧的 str() 强转是这条路径的承重墙。"""
    store = _make_store(tmp_path / "inputs")
    prompt, items = _adapter(store, {"prompt": "做个页面", "inputs": [12345]})
    assert items == [], "非 32 位 hex 的 id 应被 describe 过滤掉"
    assert prompt == "做个页面"


def test_application_path_rejects_empty_prompt_without_attachments(tmp_path: Path) -> None:
    """空 prompt 且无附件时，application 层必须拒绝——这是 generate 侧的真实行为。"""
    from htmlninefox.application import GenerationError

    store = _make_store(tmp_path / "inputs")
    with pytest.raises(GenerationError) as caught:
        _application(store, "", ())
    assert caught.value.code == "prompt_required"


def test_adapter_omits_non_dict_description_shape(tmp_path: Path) -> None:
    """describe() 只收 dict；_json_object 因此是 no-op，两侧形状天然一致。"""
    store = _make_store(tmp_path / "inputs")
    _, adapter_items = _adapter(store, {"prompt": "x", "inputs": [INPUT_ID]})
    _, app_items = _application(store, "x", (INPUT_ID,))
    assert all(isinstance(item, dict) for item in adapter_items)
    assert adapter_items == app_items
