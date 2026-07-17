export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'GET') {
      return new Response(JSON.stringify({ ok: true, message: 'Worker is alive' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const update = await request.json();
      const message = update?.message || null;
      const text = (message?.text || '').trim();
      const chatId = message?.chat?.id;

      if (!text || !chatId) {
        return new Response('ok', { status: 200 });
      }

      const allowedChatId = env.ALLOWED_CHAT_ID || '';
      if (allowedChatId && String(chatId) !== String(allowedChatId)) {
        if (env.BOT_TOKEN) {
          await sendTelegramMessage(env.BOT_TOKEN, chatId, 'Access denied');
        } else {
          console.warn('Access denied, but BOT_TOKEN is missing; no message sent');
        }
        return new Response('ok', { status: 200 });
      }

      const command = text.split(/\s+/)[0].toLowerCase();
      let responseText = '';
      let state = null;

      if (command === '/balance') {
        const amount = parseFloat(text.split(/\s+/)[1]);
        if (!Number.isFinite(amount) || amount <= 0) {
          responseText = 'Usage: /balance <amount_usd>';
        } else {
          state = { balance_usd: amount, risk_pct: null, last_updated: new Date().toISOString() };
          responseText = `✅ Balance saved: $${amount.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
        }
      } else if (command === '/procent' || command === '/risk') {
        const pct = parseFloat(text.split(/\s+/)[1]);
        if (!Number.isFinite(pct) || pct <= 0) {
          responseText = 'Usage: /procent <risk_pct>';
        } else {
          state = { balance_usd: null, risk_pct: pct, last_updated: new Date().toISOString() };
          responseText = `✅ Risk saved: ${pct}%`;
        }
      } else {
        responseText = 'Available commands:\n/balance <amount_usd>\n/procent <risk_pct>';
      }

      if (state) {
        try {
          await writePositionStateToGithub(env, state);
        } catch (writeError) {
          console.error('Failed to save state to GitHub:', writeError);
          responseText += '\n⚠️ Не удалось сохранить состояние: ' + String(writeError.message);
        }
      }

      if (env.BOT_TOKEN) {
        try {
          await sendTelegramMessage(env.BOT_TOKEN, chatId, responseText);
        } catch (sendError) {
          console.error('Failed to send Telegram message:', sendError);
          responseText += '\n⚠️ Не удалось отправить ответ в Telegram: ' + String(sendError.message);
        }
      }

      return new Response('ok', { status: 200 });
    } catch (error) {
      return new Response(JSON.stringify({ ok: false, error: String(error) }), {
        status: 500,
        headers: { 'content-type': 'application/json' },
      });
    }
  },
};

async function writePositionStateToGithub(env, state) {
  const owner = env.GITHUB_OWNER;
  const repo = env.GITHUB_REPO;
  const token = env.GITHUB_TOKEN;
  const branch = env.GITHUB_BRANCH || 'main';
  const path = env.GITHUB_FILE_PATH || 'data/position_state.json';

  if (!owner || !repo || !token) {
    console.warn('GitHub env vars missing, skipping state save');
    return;
  }

  const current = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${path}?ref=${branch}`, {
    headers: {
      'Accept': 'application/vnd.github+json',
      'Authorization': `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'Cloudflare-Worker',
    },
  });

  let sha = null;
  let existingContent = null;
  if (current.ok) {
    const currentJson = await current.json();
    sha = currentJson.sha;
    existingContent = currentJson.content ? atob(currentJson.content.replace(/\n/g, '')) : null;
  }

  let existingState = {};
  if (existingContent) {
    try {
      existingState = JSON.parse(existingContent);
    } catch {
      existingState = {};
    }
  }

  const mergedState = { ...existingState, ...state, last_updated: state.last_updated };
  const contentText = JSON.stringify(mergedState, null, 2);
  const contentBase64 = toBase64(contentText);

  const body = {
    message: `Update position state via worker`,
    content: contentBase64,
    branch,
  };

  if (sha) {
    body.sha = sha;
  }

  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${path}`, {
    method: 'PUT',
    headers: {
      'Accept': 'application/vnd.github+json',
      'Authorization': `Bearer ${token}`,
      'X-GitHub-Api-Version': '2022-11-28',
      'Content-Type': 'application/json',
      'User-Agent': 'Cloudflare-Worker',
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`GitHub update failed: ${response.status} ${errText}`);
  }
}

async function sendTelegramMessage(botToken, chatId, text) {
  if (!botToken) {
    throw new Error('BOT_TOKEN is missing');
  }

  const response = await fetch(`https://api.telegram.org/bot${botToken}/sendMessage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'HTML',
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Telegram send failed: ${response.status} ${errorText}`);
  }
}

function toBase64(str) {
  return btoa(String.fromCharCode(...new TextEncoder().encode(str)));
}
