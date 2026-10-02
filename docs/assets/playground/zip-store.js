// SPDX-License-Identifier: MIT
// A small ZIP writer for fixed project filenames. Entries use ZIP's stored method.
const encoder = new TextEncoder();
const crcTable = Uint32Array.from({ length: 256 }, (_, value) => {
  for (let bit = 0; bit < 8; bit++) value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
  return value >>> 0;
});

function crc32(bytes) {
  let value = 0xffffffff;
  for (const byte of bytes) value = (value >>> 8) ^ crcTable[(value ^ byte) & 255];
  return (value ^ 0xffffffff) >>> 0;
}

export function storeZip(files) {
  if (!files.length || files.length > 65535) throw new Error('Invalid project file count.');
  const names = new Set();
  const entries = files.map(({ name, bytes }) => {
    if (typeof name !== 'string' || name.startsWith('/') || /[\\\x00-\x1f:]/.test(name)
        || name.split('/').some(part => !part || part === '.' || part === '..') || names.has(name)) {
      throw new Error('Invalid project filename.');
    }
    names.add(name);
    const encoded = encoder.encode(name);
    if (encoded.length > 65535 || !(bytes instanceof Uint8Array) || bytes.length > 0xffffffff) {
      throw new Error('Project file exceeds ZIP limits.');
    }
    return { name: encoded, bytes, crc: crc32(bytes) };
  });
  const localSize = entries.reduce((size, file) => size + 30 + file.name.length + file.bytes.length, 0);
  const directorySize = entries.reduce((size, file) => size + 46 + file.name.length, 0);
  if (localSize + directorySize + 22 > 0xffffffff) throw new Error('Project exceeds ZIP limits.');
  const result = new Uint8Array(localSize + directorySize + 22);
  const view = new DataView(result.buffer);
  const u16 = (offset, value) => view.setUint16(offset, value, true);
  const u32 = (offset, value) => view.setUint32(offset, value, true);
  let local = 0, directory = localSize;
  for (const file of entries) {
    u32(local, 0x04034b50); u16(local + 4, 20); u16(local + 6, 0x800);
    u16(local + 12, 0x21); // Fixed 1980-01-01 date keeps identical inputs repeatable.
    u32(local + 14, file.crc); u32(local + 18, file.bytes.length); u32(local + 22, file.bytes.length);
    u16(local + 26, file.name.length);
    result.set(file.name, local + 30);
    result.set(file.bytes, local + 30 + file.name.length);

    u32(directory, 0x02014b50); u16(directory + 4, 0x0314); u16(directory + 6, 20);
    u16(directory + 8, 0x800); u16(directory + 14, 0x21);
    u32(directory + 16, file.crc); u32(directory + 20, file.bytes.length); u32(directory + 24, file.bytes.length);
    u16(directory + 28, file.name.length); u32(directory + 38, 0o100644 << 16); u32(directory + 42, local);
    result.set(file.name, directory + 46);
    local += 30 + file.name.length + file.bytes.length;
    directory += 46 + file.name.length;
  }
  u32(directory, 0x06054b50); u16(directory + 8, entries.length); u16(directory + 10, entries.length);
  u32(directory + 12, directorySize); u32(directory + 16, localSize);
  return result;
}
