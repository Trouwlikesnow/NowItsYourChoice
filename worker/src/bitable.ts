import type { Env } from "./index";
import { getTenantAccessToken } from "./feishu";

export async function createTradeRecord(
  env: Env,
  fields: Record<string, unknown>
): Promise<void> {
  const token = await getTenantAccessToken(env);
  const url = `https://open.feishu.cn/open-apis/bitable/v1/apps/${env.FEISHU_BASE_APP_TOKEN}/tables/${env.TABLE_ID_TRADES}/records`;

  const resp = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ fields }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Bitable create failed: ${resp.status} ${text}`);
  }

  const data = (await resp.json()) as { code: number; msg?: string };
  if (data.code !== 0) {
    throw new Error(`Bitable error: ${JSON.stringify(data)}`);
  }
}
