import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export const name = 'htmlninefox';
export const inject = ['skills'];

// The host owns skill discovery, invocation policy and effect disposal.
// Resolve bundled resources from this module, never from the user's cwd.
export function apply(ctx) {
  const resource = new URL('./workflow.md', import.meta.url);
  ctx.skills.register({
    name: 'htmlninefox',
    description: '用 Html九尾狐生成单文件 HTML、落地页、海报、演示页和看板，进行反馈迭代，导出 PDF / PNG。Create, revise and export local HTML projects.',
    source: 'runtime',
    invocation: { modelInvocable: true, userInvocable: true },
    path: fileURLToPath(resource),
    resourceBase: { kind: 'directory', path: fileURLToPath(new URL('.', import.meta.url)) },
    content: readFileSync(resource, 'utf8'),
  });
}
