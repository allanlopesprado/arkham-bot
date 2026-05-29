// Cloudflare Worker entry point: CORS preflight, origin gate, and route dispatch.
// Business logic lives in the focused modules imported below; this file only routes.
import { getAllowedOrigin, preflightResponse, jsonResponse, withCors, notFound } from './http.js';
import { requireAuth, requireAdmin, requireOwner } from './auth.js';
import { AI_PROVIDERS } from './validation.js';
import { handleMe, handleStatus, handleOverview } from './handlers/status.js';
import { handleGetSettings, handlePatchSettings } from './handlers/settings.js';
import { handleCommands, handleCancelCommand, handleBotCommand } from './handlers/commands.js';
import { handleCardsSearch } from './handlers/cards.js';
import { handleGetPacks } from './handlers/packs.js';
import { handleGetHistory } from './handlers/history.js';
import { handleBotInfo } from './handlers/bot-info.js';
import { handleBotRuntime } from './handlers/runtime.js';
import { handleGetAdmins, handleAddAdmin, handleRemoveAdmin } from './handlers/admins.js';
import {
  handleGetDestinations,
  handleAddDestination,
  handleGetPendingDestinations,
  handleAcceptPendingDestination,
  handleDismissPendingDestination,
  handleResolveDestination,
  handleUpdateDestination,
  handleDeleteDestination,
  handleTestDestination,
} from './handlers/destinations.js';

// Compatibility re-exports: tests import these named functions from index.js.
export { validateTelegramInitData, getAdminAccess } from './auth.js';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const { pathname } = url;
    const ao = getAllowedOrigin(request, env);

    if (request.method === 'OPTIONS') return preflightResponse(ao);

    if (pathname === '/health' && request.method === 'GET') {
      return jsonResponse({ ok: true });
    }

    if (!ao) {
      return jsonResponse({ error: 'origin_not_allowed' }, 403);
    }

    if (pathname === '/status' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/status');
      if (auth.response) return auth.response;
      return handleStatus(request, env, ao);
    }

    if (pathname === '/me' && request.method === 'GET') {
      const auth = await requireAuth(request, env, ao, '/me');
      if (auth.response) return auth.response;
      return handleMe(request, env, auth.user, ao);
    }

    if (pathname === '/overview' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/overview');
      if (auth.response) return auth.response;
      return handleOverview(request, env, auth.user, ao);
    }

    if (pathname === '/settings' && (request.method === 'GET' || request.method === 'PATCH')) {
      const auth = await requireAdmin(request, env, ao, '/settings');
      if (auth.response) return auth.response;
      if (request.method === 'GET') return handleGetSettings(env, ao);
      return handlePatchSettings(request, env, auth.user, ao);
    }

    if (pathname === '/commands' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/commands');
      if (auth.response) return auth.response;
      return handleCommands(request, env, ao);
    }

    if (pathname.startsWith('/commands/') && request.method === 'PATCH') {
      const auth = await requireAdmin(request, env, ao, '/commands/:id');
      if (auth.response) return auth.response;
      const commandId = pathname.split('/').filter(Boolean)[1] || '';
      return handleCancelCommand(request, env, auth.user, ao, commandId);
    }

    if (pathname === '/cards' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/cards');
      if (auth.response) return auth.response;
      return handleCardsSearch(request, env, ao);
    }

    if (pathname === '/packs' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/packs');
      if (auth.response) return auth.response;
      return handleGetPacks(env, ao);
    }

    if (pathname === '/history' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/history');
      if (auth.response) return auth.response;
      return handleGetHistory(request, env, ao);
    }

    if (pathname === '/bot-info' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/bot-info');
      if (auth.response) return auth.response;
      return handleBotInfo(env, ao);
    }

    if ((pathname === '/bot-command' || pathname === '/') && request.method === 'POST') {
      const auth = await requireAuth(request, env, ao, pathname);
      if (auth.response) return auth.response;
      return handleBotCommand(request, env, auth.user, ao);
    }

    if (pathname === '/ai-models' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/ai-models');
      if (auth.response) return auth.response;
      return withCors(jsonResponse({ ok: true, providers: AI_PROVIDERS }), ao);
    }

    // /bot-runtime
    if (pathname === '/bot-runtime' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/bot-runtime');
      if (auth.response) return auth.response;
      return handleBotRuntime(env, ao);
    }

    // /admins
    if (pathname === '/admins' && request.method === 'GET') {
      const auth = await requireOwner(request, env, ao, '/admins');
      if (auth.response) return auth.response;
      return handleGetAdmins(env, ao);
    }
    if (pathname === '/admins' && request.method === 'POST') {
      const auth = await requireOwner(request, env, ao, '/admins');
      if (auth.response) return auth.response;
      return handleAddAdmin(request, env, auth.user, ao);
    }
    const adminsDeleteMatch = pathname.match(/^\/admins\/(\d+)$/);
    if (adminsDeleteMatch && request.method === 'DELETE') {
      const auth = await requireOwner(request, env, ao, '/admins/:id');
      if (auth.response) return auth.response;
      return handleRemoveAdmin(request, env, auth.user, ao, adminsDeleteMatch[1]);
    }

    // /destinations
    if (pathname === '/destinations/pending' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/destinations/pending');
      if (auth.response) return auth.response;
      return handleGetPendingDestinations(env, ao);
    }
    if (pathname.startsWith('/destinations/pending/') && request.method === 'POST') {
      const pendingId = pathname.replace('/destinations/pending/', '').replace('/accept', '');
      const auth = await requireAdmin(request, env, ao, '/destinations/pending/:id/accept');
      if (auth.response) return auth.response;
      return handleAcceptPendingDestination(request, env, auth.user, ao, pendingId);
    }
    if (pathname.startsWith('/destinations/pending/') && request.method === 'DELETE') {
      const pendingId = pathname.replace('/destinations/pending/', '');
      const auth = await requireAdmin(request, env, ao, '/destinations/pending/:id');
      if (auth.response) return auth.response;
      return handleDismissPendingDestination(env, auth.user, ao, pendingId);
    }
    if (pathname === '/destinations' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/destinations');
      if (auth.response) return auth.response;
      return handleGetDestinations(env, ao);
    }
    if (pathname === '/destinations' && request.method === 'POST') {
      const auth = await requireAdmin(request, env, ao, '/destinations');
      if (auth.response) return auth.response;
      return handleAddDestination(request, env, auth.user, ao);
    }
    if (pathname === '/destinations/resolve' && request.method === 'GET') {
      const auth = await requireAdmin(request, env, ao, '/destinations/resolve');
      if (auth.response) return auth.response;
      return handleResolveDestination(request, env, ao);
    }
    const destTestMatch = pathname.match(/^\/destinations\/([^/]+)\/test$/);
    if (destTestMatch && request.method === 'POST') {
      const auth = await requireAdmin(request, env, ao, '/destinations/:id/test');
      if (auth.response) return auth.response;
      return handleTestDestination(request, env, auth.user, ao, destTestMatch[1]);
    }
    const destMatch = pathname.match(/^\/destinations\/([^/]+)$/);
    if (destMatch) {
      if (request.method === 'PATCH') {
        const auth = await requireAdmin(request, env, ao, '/destinations/:id');
        if (auth.response) return auth.response;
        return handleUpdateDestination(request, env, auth.user, ao, destMatch[1]);
      }
      if (request.method === 'DELETE') {
        const auth = await requireAdmin(request, env, ao, '/destinations/:id');
        if (auth.response) return auth.response;
        return handleDeleteDestination(request, env, auth.user, ao, destMatch[1]);
      }
    }

    if (pathname === '/me' || pathname === '/status' || pathname === '/overview' || pathname === '/settings' || pathname === '/commands' || pathname.startsWith('/commands/') || pathname === '/cards' || pathname === '/packs' || pathname === '/bot-info' || pathname === '/bot-command' || pathname === '/' || pathname === '/history' || pathname === '/ai-models' || pathname === '/bot-runtime' || pathname === '/admins' || pathname.startsWith('/admins/') || pathname === '/destinations' || pathname.startsWith('/destinations/')) {
      return withCors(jsonResponse({ error: 'method_not_allowed' }, 405), ao);
    }

    return notFound(ao);
  },
};
