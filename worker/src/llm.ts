import type { Env } from "./index";

export interface TradeRecord {
  code: string;
  name: string;
  direction: string;
  price: number;
  quantity: number;
  amount: number;
  commission: number | null;
  stamp_tax: number | null;
  transfer_fee: number | null;
  time: string | null;
}

export interface RecognitionResult {
  broker: string | null;
  trades: TradeRecord[];
  error?: string;
}

const SYSTEM_PROMPT = `你是一个券商成交记录识别助手。请从这张截图中提取所有成交记录。

要求：
1. 识别每笔交易的：股票代码、股票名称、买卖方向、成交价格、成交数量、成交金额
2. 如果能识别到佣金、印花税、过户费等手续费明细，也提取出来
3. 重要：请根据 App 界面风格、Logo、配色、顶部标题等特征判断是哪家券商（常见：华泰证券/涨乐财富通、招商证券），填入 broker 字段。如果无法确定，设为 null
4. 如果无法识别某个字段，设为 null
5. 如果截图不是成交记录，返回 {"error": "非成交记录截图"}

严格按以下 JSON 格式返回，不要附加任何说明文字：
{
  "broker": "招商证券",
  "trades": [
    {
      "code": "002594",
      "name": "比亚迪",
      "direction": "买入",
      "price": 285.50,
      "quantity": 500,
      "amount": 142750.00,
      "commission": 35.69,
      "stamp_tax": 0,
      "transfer_fee": 1.43,
      "time": "2026-05-13 14:30:00"
    }
  ]
}`;

export async function recognizeTradeScreenshot(
  env: Env,
  imageBase64: string
): Promise<RecognitionResult> {
  const resp = await fetch(`${env.LLM_API_BASE}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.LLM_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: env.LLM_MODEL,
      messages: [
        { role: "system", content: SYSTEM_PROMPT },
        {
          role: "user",
          content: [
            {
              type: "image_url",
              image_url: { url: `data:image/png;base64,${imageBase64}` },
            },
            { type: "text", text: "请识别这张成交记录截图。" },
          ],
        },
      ],
      temperature: 0.1,
      max_tokens: 2000,
    }),
  });

  if (!resp.ok) {
    throw new Error(`LLM API error: ${resp.status}`);
  }

  const data = (await resp.json()) as {
    choices: { message: { content: string } }[];
  };

  const content = data.choices?.[0]?.message?.content?.trim();
  if (!content) {
    throw new Error("Empty LLM response");
  }

  // Strip markdown code fences if present
  const jsonStr = content.replace(/^```(?:json)?\s*/, "").replace(/\s*```$/, "");
  return JSON.parse(jsonStr) as RecognitionResult;
}
