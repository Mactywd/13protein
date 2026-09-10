import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

import chat from './routes/chat.js';
import { listChats, getChat } from './routes/chats.js';
import { getChatSettings, putChatSettings } from './routes/chat-settings.js';
import track from './routes/track.js';
import report, { reportStats } from './routes/report.js';
import { loginHandler, requirePerm, requireAuth } from './lib/admin-auth.js';
import { listAdminUsers, createAdminUser, updateAdminUser, deleteAdminUser } from './routes/admin-users.js';
import { rateLimit } from './lib/rate-limit.js';
import chatSkip from './routes/chat-skip.js';
import { startRetentionLoop } from './lib/retention.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
app.set('trust proxy', 1);
const PORT = process.env.PORT || 3000;

// JSON body parsing
app.use(express.json());

// Security headers
app.use((req, res, next) => {
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  next();
});

// CORS for /api routes
app.use('/api', (req, res, next) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// Wrap async route handlers so errors are caught by Express instead of crashing the process
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

// Rate limits on the unauthenticated routes. Generous for real users (a chat
// turn every 2s sustained would still pass), tight where it matters (login
// brute force).
const chatLimit = rateLimit('chat', { windowMs: 60_000, max: 30 });
const loginLimit = rateLimit('login', { windowMs: 5 * 60_000, max: 10 });
const trackLimit = rateLimit('track', { windowMs: 60_000, max: 120 });

// API routes
app.post('/api/track', trackLimit, track);
app.post('/api/chat', chatLimit, asyncHandler(chat));
// Admin auth + protected admin routes
app.post('/api/admin/login', loginLimit, loginHandler);
const chatPerm = requirePerm('chat');
const resocontoPerm = requirePerm('resoconto');
const userMgmt = requirePerm('user-management');
app.get('/api/admin/users', userMgmt, asyncHandler(listAdminUsers));
app.post('/api/admin/users', userMgmt, asyncHandler(createAdminUser));
app.put('/api/admin/users/:user', userMgmt, asyncHandler(updateAdminUser));
app.delete('/api/admin/users/:user', userMgmt, asyncHandler(deleteAdminUser));
app.get('/api/chats', chatPerm, asyncHandler(listChats));
app.get('/api/chats/:id', chatPerm, asyncHandler(getChat));
app.get('/api/chat-settings', chatPerm, asyncHandler(getChatSettings));
app.put('/api/chat-settings', chatPerm, asyncHandler(putChatSettings));
app.get('/api/report/stats', resocontoPerm, asyncHandler(reportStats));
app.get('/api/report', resocontoPerm, asyncHandler(report));
app.post('/api/chat/skip', requireAuth(), asyncHandler(chatSkip));

// Unified admin app — serve admin.html for /admin and every subpath so the
// client-side router (BrowserRouter basename="/admin") handles refresh/deep-links.
app.get(['/admin', '/admin/*'], (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'dist', 'admin.html'));
});

// Static files
app.use(express.static(path.join(__dirname, '..', 'dist')));

// SPA fallback
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'));
});

// Global error handler - prevents unhandled errors from crashing the process.
// The full error goes to the logs only; internals are not echoed to clients.
app.use((err, req, res, next) => {
  console.error('Unhandled route error:', err);
  if (res.headersSent) {
    return res.end();
  }
  res.status(500).json({ error: 'Internal server error' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Server running on port ${PORT}`);
  // Retention purge dello store su disco (analytics JSONL), art. 5.1.e GDPR:
  // la metà su Postgres gira nel backend.
  // ATTENZIONE: di default CANCELLA. Senza RETENTION_DRY_RUN il job elimina
  // davvero, e la cancellazione non raggiunge i backup. `RETENTION_DRY_RUN=true`
  // nella ./.env di root lo riporta a contare, su entrambe le metà del purge.
  startRetentionLoop();
});
