import type { Env } from "./index";

let cachedToken: { token: string; expiresAt: number } | null = null;

export async function getTenantAccessToken(env: Env): Promise<string> {
  const now = Date.now() / 1000;
  if (cachedToken && now < cachedToken.expiresAt - 60) {
    return cachedToken.token;
  }

  const resp = await fetch(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        app_id: env.FEISHU_APP_ID,
        app_secret: env.FEISHU_APP_SECRET,
      }),
    }
  );
  const data = (await resp.json()) as {
    code: number;
    tenant_access_token: string;
    expire: number;
  };
  if (data.code !== 0) {
    throw new Error(`Feishu token error: ${JSON.stringify(data)}`);
  }
  cachedToken = {
    token: data.tenant_access_token,
    expiresAt: now + data.expire,
  };
  return data.tenant_access_token;
}

export async function downloadImage(
  env: Env,
  messageId: string,
  imageKey: string
): Promise<ArrayBuffer> {
  const token = await getTenantAccessToken(env);
  const url = `https://open.feishu.cn/open-apis/im/v1/messages/${messageId}/resources/${imageKey}?type=image`;
  const resp = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    throw new Error(`Image download failed: ${resp.status}`);
  }
  return resp.arrayBuffer();
}

export async function replyMessage(
  env: Env,
  messageId: string,
  text: string
): Promise<void> {
  const token = await getTenantAccessToken(env);
  const resp = await fetch(
    `https://open.feishu.cn/open-apis/im/v1/messages/${messageId}/reply`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        content: JSON.stringify({ text }),
        msg_type: "text",
      }),
    }
  );
  if (!resp.ok) {
    console.error("Reply failed:", resp.status, await resp.text());
  }
}
