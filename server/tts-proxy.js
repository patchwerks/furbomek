const express = require('express');
const cors = require('cors');
const {pipeline} = require('stream');

const app = express();
const PORT = 3500;

app.use(cors());
app.use(express.json());

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
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).send(error.message);
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
    const data = await subscriptionInfo.json();

    res.json(data);
  } catch (error) {
    res.status(500).send(error.message);
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

    response.headers.forEach((value, name) => {
      res.setHeader(name, value);
    });

    res.status(response.status);

    pipeline(response.body, res, (err) => {
      if (err) {
        console.log("[PROXY]Pipeline failed.", err);
      } else {
        console.log('[PROXY]Pipeline succeeded.')
      }
    });
  } catch (error) {
    res.status(500).send(error.message);
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

    const data = await response.json()

    res.json(data);
  } catch (error) {
    res.status(500).send(error.message);
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

    const data = await response.json()

    res.json(data);
  } catch (error) {
    res.status(500).send(error.message);
  }
});


app.listen(PORT, () => {
  console.log(`Proxy server running on http://localhost:${PORT}`);
});
