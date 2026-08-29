import { configureStore, createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  activatePortfolio,
  getActivityLog,
  getAdminUserPortfolio,
  getCurrentUser,
  getPortfolioDashboard,
  getPortfolioHoldingSymbols,
  getPortfolioOperations,
  getPortfolioPerformance,
  getPortfolioRisk,
  listPortfolioSnapshots,
  listPortfolios,
  listPortfolioTransactionAudit,
  listPortfolioTransactions,
  syncPortfolio,
} from './api.js';

const STORAGE_KEY = 'qport.redux-cache.v1';
const STORAGE_VERSION = 1;
const CACHE_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const MAX_PERSISTED_ROUTES = 16;

function todayVn() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function readPersistedState() {
  if (typeof window === 'undefined') return null;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || 'null');
    if (!parsed || parsed.version !== STORAGE_VERSION) return null;
    return parsed;
  } catch {
    return null;
  }
}

const persisted = readPersistedState();

function activePortfolioId(state) {
  return Number(state.qport?.registry?.active_portfolio_id || 0);
}

function routeKey(pathname, portfolioId = 0) {
  const accountScoped = pathname === '/admin' || pathname.startsWith('/admin/');
  return `${accountScoped ? 'account' : portfolioId || 'default'}:${pathname}`;
}

async function fetchRoutePayload(pathname) {
  const adminUserMatch = pathname.match(/^\/admin\/users\/(\d+)$/);
  if (adminUserMatch) {
    return { payload: await getAdminUserPortfolio(Number(adminUserMatch[1])) };
  }

  switch (pathname) {
    case '/':
      return { dashboard: await getPortfolioDashboard() };
    case '/portfolios':
      return { registry: await listPortfolios() };
    case '/transactions': {
      const [transactions, corrections] = await Promise.all([
        listPortfolioTransactions(),
        listPortfolioTransactionAudit(),
      ]);
      return { transactions, corrections, today: todayVn() };
    }
    case '/performance':
      return { performance: await getPortfolioPerformance() };
    case '/risk': {
      const [risk, snapshots] = await Promise.all([
        getPortfolioRisk(),
        listPortfolioSnapshots(),
      ]);
      return { risk, snapshots };
    }
    case '/valuation':
      return { symbols: await getPortfolioHoldingSymbols() };
    case '/dividends':
      return { symbols: await getPortfolioHoldingSymbols() };
    case '/snapshots':
      return { snapshots: await listPortfolioSnapshots() };
    case '/operations':
      return { operations: await getPortfolioOperations(), today: todayVn() };
    case '/logs':
      return { activity: await getActivityLog() };
    case '/settings':
      return { dashboard: await getPortfolioDashboard() };
    case '/screener':
    case '/guide':
    case '/admin':
    case '/admin/auth':
    case '/admin/finance-data':
      return {};
    default:
      throw new Error('Trang không tồn tại.');
  }
}


export const bootstrapApp = createAsyncThunk('qport/bootstrap', async () => {
  const me = await getCurrentUser();
  const user = me?.user || null;
  const registry = user && user.role !== 'ADMIN' ? await listPortfolios() : null;
  return { user, registry };
});

export const loadRoute = createAsyncThunk(
  'qport/loadRoute',
  async ({ pathname }, { getState }) => {
    const portfolioId = activePortfolioId(getState());
    const key = routeKey(pathname, portfolioId);
    return {
      key,
      pathname,
      portfolioId,
      data: await fetchRoutePayload(pathname),
      updatedAt: Date.now(),
    };
  },
);

export const refreshDashboard = createAsyncThunk(
  'qport/refreshDashboard',
  async (_, { getState }) => {
    const result = await syncPortfolio();
    if (!result?.dashboard) throw new Error('API đồng bộ không trả về dashboard mới.');
    const portfolioId = activePortfolioId(getState());
    return {
      key: routeKey('/', portfolioId),
      pathname: '/',
      portfolioId,
      data: { dashboard: result.dashboard },
      updatedAt: Date.now(),
    };
  },
);

export const refreshPortfolioRegistry = createAsyncThunk(
  'qport/refreshPortfolioRegistry',
  async () => listPortfolios(),
);

export const selectPortfolio = createAsyncThunk(
  'qport/selectPortfolio',
  async (portfolioId) => {
    await activatePortfolio(portfolioId);
    return listPortfolios();
  },
);

const initialState = {
  bootStatus: 'idle',
  bootError: '',
  user: null,
  ownerId: persisted?.ownerId || null,
  registry: persisted?.registry || null,
  routes: persisted?.routes || {},
  refreshStatus: 'idle',
  refreshError: '',
};

const qportSlice = createSlice({
  name: 'qport',
  initialState,
  reducers: {
    resetClientState: () => ({
      ...initialState,
      bootStatus: 'idle',
      ownerId: null,
      registry: null,
      routes: {},
    }),
    invalidateRoute(state, action) {
      const pathname = action.payload;
      delete state.routes[routeKey(pathname, Number(state.registry?.active_portfolio_id || 0))];
    },
  },
  extraReducers: builder => {
    builder
      .addCase(bootstrapApp.pending, state => {
        state.bootStatus = 'loading';
        state.bootError = '';
      })
      .addCase(bootstrapApp.fulfilled, (state, action) => {
        const nextOwnerId = action.payload.user?.id ?? null;
        if (String(state.ownerId ?? '') !== String(nextOwnerId ?? '')) {
          state.routes = {};
          state.registry = null;
        }
        state.user = action.payload.user;
        state.ownerId = nextOwnerId;
        state.registry = action.payload.registry;
        state.bootStatus = 'ready';
      })
      .addCase(bootstrapApp.rejected, (state, action) => {
        state.user = null;
        state.bootStatus = 'failed';
        state.bootError = action.error.message || 'Không thể xác minh phiên đăng nhập.';
      })
      .addCase(loadRoute.pending, (state, action) => {
        const key = routeKey(
          action.meta.arg.pathname,
          Number(state.registry?.active_portfolio_id || 0),
        );
        const previous = state.routes[key] || {};
        state.routes[key] = {
          ...previous,
          pathname: action.meta.arg.pathname,
          status: 'loading',
          error: '',
        };
      })
      .addCase(loadRoute.fulfilled, (state, action) => {
        state.routes[action.payload.key] = {
          ...action.payload,
          status: 'ready',
          error: '',
        };
        if (action.payload.pathname === '/portfolios' && action.payload.data.registry) {
          state.registry = action.payload.data.registry;
        }
      })
      .addCase(loadRoute.rejected, (state, action) => {
        const key = routeKey(
          action.meta.arg.pathname,
          Number(state.registry?.active_portfolio_id || 0),
        );
        state.routes[key] = {
          ...(state.routes[key] || {}),
          pathname: action.meta.arg.pathname,
          status: 'failed',
          error: action.error.message || 'Không thể tải dữ liệu.',
        };
      })
      .addCase(refreshDashboard.pending, state => {
        state.refreshStatus = 'loading';
        state.refreshError = '';
      })
      .addCase(refreshDashboard.fulfilled, (state, action) => {
        state.routes[action.payload.key] = {
          ...action.payload,
          status: 'ready',
          error: '',
        };
        state.refreshStatus = 'ready';
      })
      .addCase(refreshDashboard.rejected, (state, action) => {
        state.refreshStatus = 'failed';
        state.refreshError = action.error.message || 'Không thể cập nhật dữ liệu.';
      })
      .addCase(refreshPortfolioRegistry.fulfilled, (state, action) => {
        state.registry = action.payload;
      })
      .addCase(selectPortfolio.pending, state => {
        state.refreshStatus = 'loading';
        state.refreshError = '';
      })
      .addCase(selectPortfolio.fulfilled, (state, action) => {
        state.registry = action.payload;
        state.refreshStatus = 'ready';
      })
      .addCase(selectPortfolio.rejected, (state, action) => {
        state.refreshStatus = 'failed';
        state.refreshError = action.error.message || 'Không thể chuyển danh mục.';
      });
  },
});

export const { invalidateRoute, resetClientState } = qportSlice.actions;

export const store = configureStore({
  reducer: { qport: qportSlice.reducer },
});

let persistTimer = null;
store.subscribe(() => {
  if (typeof window === 'undefined') return;
  if (persistTimer) return;
  persistTimer = window.setTimeout(() => {
    persistTimer = null;
    const state = store.getState().qport;
    const cutoff = Date.now() - CACHE_MAX_AGE_MS;
    const routes = Object.fromEntries(
      Object.entries(state.routes)
        .filter(([, value]) => Number(value.updatedAt || 0) >= cutoff && value.data)
        .sort((a, b) => Number(b[1].updatedAt || 0) - Number(a[1].updatedAt || 0))
        .slice(0, MAX_PERSISTED_ROUTES),
    );
    const value = {
      version: STORAGE_VERSION,
      ownerId: state.ownerId,
      registry: state.registry,
      routes,
    };
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } catch {
      try {
        window.localStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ ...value, routes: routes[routeKey('/', activePortfolioId(store.getState()))] ? {
            [routeKey('/', activePortfolioId(store.getState()))]: routes[routeKey('/', activePortfolioId(store.getState()))],
          } : {} }),
        );
      } catch {
        // Storage can be unavailable or full; Redux remains the in-memory source of truth.
      }
    }
  }, 200);
});

export function clearPersistedQPortState() {
  if (typeof window !== 'undefined') window.localStorage.removeItem(STORAGE_KEY);
}

export const selectUser = state => state.qport.user;
export const selectRegistry = state => state.qport.registry;
export const selectBootStatus = state => state.qport.bootStatus;
export const selectBootError = state => state.qport.bootError;
export const selectRefreshStatus = state => state.qport.refreshStatus;
export const selectRefreshError = state => state.qport.refreshError;
export const selectRouteState = (state, pathname) => (
  state.qport.routes[routeKey(pathname, activePortfolioId(state))] || {
    pathname,
    status: 'idle',
    data: null,
    error: '',
    updatedAt: null,
  }
);
