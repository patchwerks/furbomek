const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 3500;

app.use(cors());
app.use(express.json());

// Only fixed local messages cross the error boundary. Never serialize caught errors.
function sendError(res, status = 502, message = 'Upstream service request failed.') {
  if (res.destroyed || res.writableEnded) return;
  if (res.headersSent) {
    res.destroy();
    return;
  }
  res.status(status).json({ error: message });
}

function upstreamStatus(response) {
  const status = response.status;
  if (!Number.isInteger(status) || status < 200 || status > 599 ||
      (status >= 300 && status < 400)) return 502;
  return status;
}

function rejectUpstream(response, res) {
  const status = upstreamStatus(response);
  if (status < 300) return false;
  // Cancel without reading rejected bodies or forwarding their headers.
  try { Promise.resolve(response.body?.cancel()).catch(() => {}); } catch {}
  sendError(res, status);
  return true;
}

async function streamAudio(response, res) {
  let reader;
  const headerNames = [];
  const cancel = () => {
    if (reader) {
      try { Promise.resolve(reader.cancel()).catch(() => {}); } catch {}
    }
  };
  res.on('close', cancel);
  try {
    reader = response.body.getReader();
    if (res.destroyed) { cancel(); return; }
    // Read first, before committing provider headers/status. Early failure is JSON.
    let chunk = await reader.read();
    if (res.destroyed) return;
    response.headers.forEach((value, name) => {
      res.setHeader(name, value);
      headerNames.push(name);
    });
    res.status(response.status);
    while (!chunk.done) {
      if (!res.write(chunk.value)) {
        await new Promise(resolve => {
          const finish = () => {
            res.off('drain', finish);
            res.off('close', finish);
            resolve();
          };
          res.once('drain', finish);
          res.once('close', finish);
        });
      }
      if (res.destroyed) return;
      chunk = await reader.read();
    }
    res.end();
  } catch {
    // No pipeline owns/destroys res: early errors remain writable, late errors
    // deliberately terminate the incomplete audio response without appending JSON.
    cancel();
    if (!res.headersSent) {
      for (const name of headerNames) res.removeHeader(name);
    }
    sendError(res);
  } finally {
    res.off('close', cancel);
    if (reader) reader.releaseLock();
  }
}

app.get('/proxy/elevenlabs/voices', async (req, res) => {
  try {
    const response = await fetch('https://api.elevenlabs.io/v1/voices', {
      method: 'GET',
      headers: {
        'Accept': req.headers['Accept'],
        'xi-api-key': req.headers['xi-api-key'],
        'Content-Type': req.headers['Content-Type'],
      }
    });
    if (rejectUpstream(response, res)) return;
    const data = await response.json();
    res.json(data);
  } catch {
    sendError(res);
  }
});

app.get('/proxy/elevenlabs/subscription', async (req, res) => {
  try {
    const subscriptionInfo = await fetch('https://api.elevenlabs.io/v1/user/subscription', {
      method: 'GET',
      headers: {
        'Accept': req.headers['Accept'],
        'xi-api-key': req.headers['xi-api-key'],
        'Content-Type': req.headers['Content-Type'],
      }
    })
    if (rejectUpstream(subscriptionInfo, res)) return;
    const data = await subscriptionInfo.json();

    res.json(data);
  } catch {
    sendError(res);
  }
});


app.post('/proxy/playht/stream', async (req, res) => {
  try {
    const response = await fetch('https://api.play.ht/api/v2/tts/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': req.headers.authorization,
        'X-USER-ID': req.headers['x-user-id'],
        'accept': 'audio/wav'
      },
      body: JSON.stringify(req.body)
    });

    if (rejectUpstream(response, res)) return;
    await streamAudio(response, res);
  } catch {
    sendError(res);
  }
});


app.get('/proxy/playht/voices', async (req, res) => {
  try {
    const response = await fetch('https://api.play.ht/api/v2/voices', {
      method: "GET",
      headers: {
        'Accept': 'application/json',
        'Authorization': req.headers.authorization,
        'X-USER-ID': req.headers['x-user-id']
      }
    });

    if (rejectUpstream(response, res)) return;
    const data = await response.json()

    res.json(data);
  } catch {
    sendError(res);
  }
});

app.get('/proxy/playht/cloned-voices', async (req, res) => {
  try {
    const response = await fetch('https://api.play.ht/api/v2/cloned-voices', {
      method: "GET",
      headers: {
        'Accept': 'application/json',
        'Authorization': req.headers.authorization,
        'X-USER-ID': req.headers['x-user-id']
      }
    });

    if (rejectUpstream(response, res)) return;
    const data = await response.json()

    res.json(data);
  } catch {
    sendError(res);
  }
});


// Express parser failures must not fall through to its stack/body error page.
app.use((error, req, res, next) => {
  const parserErrors = {
    'entity.parse.failed': [400, 'Invalid JSON request body.'],
    'entity.too.large': [413, 'Request body is too large.'],
    'encoding.unsupported': [415, 'Unsupported request encoding.'],
    'charset.unsupported': [415, 'Unsupported request charset.'],
    'request.aborted': [400, 'Incomplete request body.'],
    'request.size.invalid': [400, 'Invalid request body size.'],
  };
  const known = Object.prototype.hasOwnProperty.call(parserErrors, error?.type)
    ? parserErrors[error.type] : [500, 'Internal server error.'];
  sendError(res, ...known);
});

app.listen(PORT, () => {
  console.log(`Proxy server running on http://localhost:${PORT}`);
});
