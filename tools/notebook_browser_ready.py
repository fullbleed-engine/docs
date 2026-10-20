"""Wait for a private Jupyter test server's application and kernel connection."""


def wait_for_notebook_ready(page, *, timeout_ms=60000):
    # --expose-app-in-browser is enabled only on the isolated test server.
    # An idle execution indicator can appear before the first kernel handshake.
    page.wait_for_function("() => Boolean(window.jupyterapp)", timeout=timeout_ms)
    observed = page.evaluate("""async timeoutMs => {
        let timer;
        try {
            return await Promise.race([
                (async () => {
                    const app = window.jupyterapp;
                    if (typeof app.started?.then !== 'function' ||
                        typeof app.restored?.then !== 'function') {
                        throw new Error('Expected Jupyter application readiness promises');
                    }
                    await app.started;
                    await app.restored;
                    const panel = app.shell.currentWidget;
                    if (!panel?.context || !panel?.sessionContext) {
                        throw new Error('Expected the current notebook panel');
                    }
                    await panel.context.ready;
                    await panel.sessionContext.ready;
                    const kernel = panel.sessionContext.session?.kernel;
                    if (typeof kernel?.info?.then !== 'function') {
                        throw new Error('Expected a kernel startup reply promise');
                    }
                    // Session creation can finish while the socket is connecting.
                    await kernel.info;
                    return {
                        application_readiness_promises_resolved: true,
                        session_ready: panel.sessionContext.isReady,
                        kernel_startup_reply_received: true,
                        kernel_status: kernel.status,
                        connection_status: kernel.connectionStatus
                    };
                })(),
                new Promise((_, reject) => {
                    timer = setTimeout(() => reject(new Error('Jupyter application or session did not become ready')), timeoutMs);
                })
            ]);
        } finally {
            clearTimeout(timer);
        }
    }""", timeout_ms)
    assert observed["application_readiness_promises_resolved"] and observed["session_ready"]
    assert observed["kernel_startup_reply_received"]
    assert observed["connection_status"] == "connected", observed
    return observed
