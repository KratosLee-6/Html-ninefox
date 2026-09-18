import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import test from 'node:test';
import { Context } from '@deepseek-ai/cordis';
import SkillRegistry from '@deepseek-ai/dsh-skill';
import * as plugin from '../index.js';

const packageDir = fileURLToPath(new URL('..', import.meta.url));

test('real Harness registry discovers, loads, reloads and removes the skill', async () => {
  const ctx = new Context();
  const registry = ctx.plugin(SkillRegistry);
  await registry.await();
  const fiber = ctx.plugin(plugin);
  try {
    await fiber.await();
    const catalog = await ctx.skills.list();
    assert.equal(catalog.length, 1);
    assert.equal(catalog[0].name, 'htmlninefox');
    assert.equal(catalog[0].invocation.modelInvocable, true);
    assert.equal(catalog[0].invocation.userInvocable, true);
    const skill = await ctx.skills.get('htmlninefox');
    assert.match(skill.content, /htmlninefox expert/);
    assert.match(skill.content, /htmlninefox feedback/);
    assert.match(skill.content, /htmlninefox export/);
    assert.equal(readFileSync(skill.path, 'utf8'), skill.content);
    await fiber.restart();
    assert.equal((await ctx.skills.list()).length, 1);
    await fiber.dispose();
    assert.equal((await ctx.skills.list()).length, 0);
    assert.equal(await ctx.skills.get('htmlninefox'), undefined);
  } finally {
    await fiber.dispose();
    await registry.dispose();
  }
});

test('published tarball works without the source checkout or production dependencies', async () => {
  const scratch = mkdtempSync(join(tmpdir(), 'fox harness 中文 '));
  const npmCli = process.env.npm_execpath;
  assert.ok(npmCli, 'Run through npm test so the npm CLI path is available');
  const npm = (args, cwd) => execFileSync(process.execPath, [npmCli, ...args], {
    cwd, encoding: 'utf8', timeout: 60000, stdio: ['ignore', 'pipe', 'pipe'],
  });
  const ctx = new Context();
  const registry = ctx.plugin(SkillRegistry);
  let fiber;
  try {
    await registry.await();
    const [packed] = JSON.parse(npm(['pack', '--json', '--ignore-scripts', '--pack-destination', scratch], packageDir));
    for (const file of ['index.js', 'workflow.md', 'cordis.patch.yml', 'LICENSE', 'README.md']) {
      assert.ok(packed.files.some(entry => entry.path === file), `missing ${file}`);
    }
    assert.ok(packed.files.every(entry => !entry.path.startsWith('node_modules/') && !entry.path.startsWith('test/')));
    npm(['install', '--prefix', scratch, '--ignore-scripts', '--omit=dev', '--no-audit', '--no-fund', join(scratch, packed.filename)], scratch);
    const installed = join(scratch, 'node_modules', 'dsh-htmlninefox');
    const manifest = JSON.parse(readFileSync(join(installed, 'package.json'), 'utf8'));
    assert.equal(manifest.dsh.bundle.patch, './cordis.patch.yml');
    assert.equal(manifest.dependencies, undefined);
    fiber = ctx.plugin(await import(pathToFileURL(join(installed, 'index.js')).href));
    await fiber.await();
    const skill = await ctx.skills.get('htmlninefox');
    assert.equal(skill.resourceBase.path, installed + (process.platform === 'win32' ? '\\' : '/'));
    assert.equal(skill.content, readFileSync(join(installed, 'workflow.md'), 'utf8'));
  } finally {
    await fiber?.dispose();
    await registry.dispose();
    rmSync(scratch, { recursive: true, force: true });
  }
});
