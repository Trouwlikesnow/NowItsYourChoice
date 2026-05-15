import type { Env } from "./index";
import { getTenantAccessToken } from "./feishu";

const BASE = "https://open.feishu.cn/open-apis/bitable/v1/apps";

export async function createTradeRecord(
  env: Env,
  fields: Record<string, unknown>
): Promise<void> {
  const token = await getTenantAccessToken(env);
  const url = `${BASE}/${env.FEISHU_BASE_APP_TOKEN}/tables/${env.TABLE_ID_TRADES}/records`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });

  const data = (await resp.json()) as { code: number; msg?: string };
  if (!resp.ok || data.code !== 0) {
    throw new Error(
      `Bitable create failed: ${resp.status} ${JSON.stringify(data)}`
    );
  }
}

interface PortfolioRecord {
  record_id: string;
  fields: Record<string, unknown>;
}

export async function findPortfolioPosition(
  env: Env,
  stockCode: string,
  broker: string
): Promise<PortfolioRecord | null> {
  const token = await getTenantAccessToken(env);
  const url = `${BASE}/${env.FEISHU_BASE_APP_TOKEN}/tables/${env.TABLE_ID_PORTFOLIO}/records/search`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      filter: {
        conjunction: "and",
        conditions: [
          {
            field_name: "股票代码",
            operator: "is",
            value: [stockCode],
          },
          {
            field_name: "券商",
            operator: "is",
            value: [broker],
          },
        ],
      },
    }),
  });

  const data = (await resp.json()) as {
    code: number;
    data?: { items?: { record_id: string; fields: Record<string, unknown> }[] };
  };

  if (data.code !== 0 || !data.data?.items?.length) {
    return null;
  }

  const item = data.data.items[0];
  return { record_id: item.record_id, fields: item.fields };
}

export async function updatePortfolioPosition(
  env: Env,
  recordId: string,
  fields: Record<string, unknown>
): Promise<void> {
  const token = await getTenantAccessToken(env);
  const url = `${BASE}/${env.FEISHU_BASE_APP_TOKEN}/tables/${env.TABLE_ID_PORTFOLIO}/records/${recordId}`;

  const resp = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });

  const data = (await resp.json()) as { code: number; msg?: string };
  if (!resp.ok || data.code !== 0) {
    throw new Error(
      `Portfolio update failed: ${resp.status} ${JSON.stringify(data)}`
    );
  }
}

export async function createPortfolioPosition(
  env: Env,
  fields: Record<string, unknown>
): Promise<void> {
  const token = await getTenantAccessToken(env);
  const url = `${BASE}/${env.FEISHU_BASE_APP_TOKEN}/tables/${env.TABLE_ID_PORTFOLIO}/records`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });

  const data = (await resp.json()) as { code: number; msg?: string };
  if (!resp.ok || data.code !== 0) {
    throw new Error(
      `Portfolio create failed: ${resp.status} ${JSON.stringify(data)}`
    );
  }
}
