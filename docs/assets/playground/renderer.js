// SPDX-License-Identifier: MIT
import { WASI, File, OpenFile, ConsoleStdout, PreopenDirectory } from './wasi/index.js';

export async function render(module, files) {
  const messages = [];
  const collect = line => { if (messages.join('\n').length < 4000) messages.push(line); };
  const root = new PreopenDirectory('.', new Map(Object.entries(files).map(([name, bytes]) => [name, new File(bytes)])));
  const wasi = new WASI(['fullbleed'], [], [
    new OpenFile(new File([])),
    ConsoleStdout.lineBuffered(collect),
    ConsoleStdout.lineBuffered(collect),
    root,
  ], { debug: false });
  const instance = await WebAssembly.instantiate(module, { wasi_snapshot_preview1: wasi.wasiImport });
  const exit = wasi.start(instance);
  if (exit) throw new Error(messages.join('\n') || `The engine exited with code ${exit}.`);
  const outputs = {};
  for (const [name, file] of root.dir.contents) {
    if (name === 'output.pdf' || name === 'result.json' || /^page-\d+\.png$/.test(name)) outputs[name] = file.data;
  }
  if (!outputs['output.pdf'] || !outputs['result.json']) throw new Error('The engine did not produce a PDF.');
  return { outputs, memory: instance.exports.memory.buffer.byteLength };
}
