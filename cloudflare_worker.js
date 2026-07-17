export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const payload = await request.json();
      const now = new Date().toISOString();
      const entry = { ...payload, received_at: now };

      const key = `balance-${Date.now()}.json`;
      await env.BUCKET?.put(key, JSON.stringify(entry, null, 2));

      return new Response(JSON.stringify({ ok: true, saved: key }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    } catch (error) {
      return new Response(JSON.stringify({ ok: false, error: String(error) }), {
        status: 400,
        headers: { 'content-type': 'application/json' },
      });
    }
  },
};
