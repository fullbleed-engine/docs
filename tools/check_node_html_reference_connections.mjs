// Deterministic fault injection for the separate, optional Puppeteer reference.
import assert from 'node:assert/strict';
import http from 'node:http';
import { connect } from 'node:net';
import { syncBuiltinESMExports } from 'node:module';
import { writeFileSync } from 'node:fs';

const mode = process.env.FULLBLEED_REFERENCE_CONNECTION_CASE;
assert.ok(['unused', 'partial'].includes(mode));
assert.ok(process.env.FULLBLEED_REFERENCE_CONNECTION_REPORT);
const report = { mode, node: process.version, servers: 0, connected: false,
  closeCalled: false, serverClosed: false, rescueNeeded: false, errors: [], shutdowns: [] };
const originalCreateServer = http.createServer;
http.createServer = function (...args) {
  const server = originalCreateServer.apply(this, args);
  const number = ++report.servers;
  const shutdown = { number, closeCalled: false, serverClosed: false, rescueNeeded: false };
  report.shutdowns.push(shutdown);
  let socket, deadline;
  server.once('listening', () => {
    if (number !== 2) return;
    socket = connect(server.address().port, '127.0.0.1');
    socket.on('error', error => {
      // Reset is also a valid outcome when the server terminates this socket.
      if (!shutdown.closeCalled || error.code !== 'ECONNRESET') report.errors.push(error.code ?? error.message);
    });
    socket.once('connect', () => {
      report.connected = true;
      if (mode === 'partial') socket.write('GET /document HTTP/1.1\r\nHost: localhost\r\n');
    });
  });
  const originalClose = server.close;
  server.close = function (...closeArgs) {
    report.closeCalled = true;
    shutdown.closeCalled = true;
    // Rescue only this renderer's temporary server so failures exit cleanly.
    // The deadline begins at shutdown, independently of browser/render speed.
    deadline = setTimeout(() => {
      report.rescueNeeded = true;
      shutdown.rescueNeeded = true;
      process.exitCode = 1;
      server.closeAllConnections();
    }, 2000);
    return originalClose.apply(this, closeArgs);
  };
  server.once('close', () => {
    report.serverClosed = true;
    shutdown.serverClosed = true;
    clearTimeout(deadline);
    socket?.destroy();
  });
  return server;
};
syncBuiltinESMExports();
process.once('exit', () => {
  report.ok = report.servers === 2 && report.connected && report.closeCalled && report.serverClosed
    && report.shutdowns.every(shutdown => shutdown.closeCalled && shutdown.serverClosed)
    && !report.rescueNeeded && report.errors.length === 0;
  if (!report.ok) process.exitCode = 1;
  writeFileSync(process.env.FULLBLEED_REFERENCE_CONNECTION_REPORT, JSON.stringify(report, null, 2) + '\n');
});
