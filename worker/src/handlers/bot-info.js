// Telegram bot profile endpoint (getMe + description + photo).
import { withCors, jsonResponse } from '../http.js';

export async function handleBotInfo(env, ao) {
  const token = env.TELEGRAM_BOT_TOKEN;
  if (!token) return withCors(jsonResponse({ error: 'bot_token_not_configured' }, 500), ao);

  const tgApi = (path) =>
    fetch(`https://api.telegram.org/bot${token}/${path}`, { headers: { Accept: 'application/json' } })
      .then((r) => r.json());

  try {
    // getMe returns bot id, name, username + description/short_description (Bot API 6.7+)
    const meResp = await tgApi('getMe');
    if (!meResp.ok) return withCors(jsonResponse({ error: 'telegram_api_failed' }, 502), ao);

    const bot = meResp.result;
    let photo_url = null;

    // Fetch profile photos, description and short_description in parallel
    const [photosResp, descResp, shortDescResp] = await Promise.all([
      tgApi(`getUserProfilePhotos?user_id=${bot.id}&limit=1`),
      tgApi('getMyDescription'),
      tgApi('getMyShortDescription'),
    ]);

    const fileId = photosResp.result?.photos?.[0]?.at(-1)?.file_id;
    if (fileId) {
      const fileResp = await tgApi(`getFile?file_id=${fileId}`);
      if (fileResp.ok && fileResp.result?.file_path) {
        photo_url = `https://api.telegram.org/file/bot${token}/${fileResp.result.file_path}`;
      }
    }

    return withCors(jsonResponse({
      ok: true,
      name: bot.first_name || null,
      username: bot.username || null,
      description: descResp.result?.description || null,
      short_description: shortDescResp.result?.short_description || null,
      photo_url,
    }), ao);
  } catch {
    return withCors(jsonResponse({ error: 'bot_info_fetch_failed' }, 500), ao);
  }
}
