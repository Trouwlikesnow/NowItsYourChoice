import { downloadImage, replyMessage } from "./feishu";
import { recognizeTradeScreenshot } from "./llm";
import { normalizeBroker, fillFees } from "./fees";
import { createTradeRecord } from "./bitable";

export interface Env {
  FEISHU_APP_ID: string;
  FEISHU_APP_SECRET: string;
  FEISHU_VERIFICATION_TOKEN: string;
  FEISHU_BASE_APP_TOKEN: string;
  TABLE_ID_TRADES: string;
  LLM_API_BASE: string;
  LLM_API_KEY: string;
  LLM_MODEL: string;
}

interface FeishuEvent {
  challenge?: string;
  header?: { event_type: string; token: string };
  event?: {
    message?: {
      message_id: string;
      message_type: string;
      content: string;
    };
  };
}

// Deduplicate events (Feishu may retry)
const processedEvents = new Set<string>();

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== "POST") {
      return new Response("OK", { status: 200 });
    }

    try {
      const body = (await request.json()) as FeishuEvent;

      // Challenge verification
      if (body.challenge) {
        return Response.json({ challenge: body.challenge });
      }

      // Verify token
      if (body.header?.token !== env.FEISHU_VERIFICATION_TOKEN) {
        return new Response("Unauthorized", { status: 401 });
      }

      const message = body.event?.message;
      if (!message) {
        return new Response("OK", { status: 200 });
      }

      // Deduplicate
      if (processedEvents.has(message.message_id)) {
        return new Response("OK", { status: 200 });
      }
      processedEvents.add(message.message_id);

      // Only handle image messages
      if (message.message_type !== "image") {
        await replyMessage(
          env,
          message.message_id,
          "请发送券商成交记录的截图，我来帮你识别录入。"
        );
        return new Response("OK", { status: 200 });
      }

      // Extract image_key from content JSON
      const content = JSON.parse(message.content) as { image_key: string };
      const imageKey = content.image_key;

      // Download image
      let imageBuffer: ArrayBuffer;
      try {
        imageBuffer = await downloadImage(env, message.message_id, imageKey);
      } catch (e) {
        await replyMessage(env, message.message_id, "❌ 图片获取失败，请重新发送");
        return new Response("OK", { status: 200 });
      }

      // Convert to base64
      const imageBase64 = btoa(
        String.fromCharCode(...new Uint8Array(imageBuffer))
      );

      // Call LLM
      let result;
      try {
        result = await recognizeTradeScreenshot(env, imageBase64);
      } catch (e) {
        await replyMessage(env, message.message_id, "❌ 识别异常，请手动录入");
        return new Response("OK", { status: 200 });
      }

      if (result.error) {
        await replyMessage(
          env,
          message.message_id,
          `❌ 无法识别：${result.error}`
        );
        return new Response("OK", { status: 200 });
      }

      if (!result.trades || result.trades.length === 0) {
        await replyMessage(env, message.message_id, "❌ 未识别到任何交易记录");
        return new Response("OK", { status: 200 });
      }

      // Write to Bitable
      const broker = normalizeBroker(result.broker);
      const lines: string[] = [];

      for (let i = 0; i < result.trades.length; i++) {
        const trade = result.trades[i];
        const fees = fillFees(trade, broker);

        const fields: Record<string, unknown> = {
          股票代码: trade.code,
          股票名称: trade.name,
          方向: trade.direction,
          成交价: trade.price,
          成交数量: trade.quantity,
          成交金额: trade.amount,
          佣金: fees.commission,
          印花税: fees.stampTax,
          过户费: fees.transferFee,
          手续费合计: fees.total,
          券商: broker,
          来源: "截图识别",
          识别状态: "已确认",
        };

        if (trade.time) {
          fields["交易时间"] = new Date(trade.time).getTime();
        }

        try {
          await createTradeRecord(env, fields);
        } catch (e) {
          console.error(`Failed to write trade ${i}:`, e);
          await replyMessage(env, message.message_id, "❌ 写入失败，请稍后重试");
          return new Response("OK", { status: 200 });
        }

        const feeStr = fees.total > 0 ? `  手续费 ${fees.total}` : "";
        lines.push(
          `${i + 1}. ${trade.direction} ${trade.name}(${trade.code}) ` +
            `${trade.quantity}股 × ${trade.price} = ${trade.amount.toLocaleString()}${feeStr}`
        );
      }

      const reply =
        `✅ 已录入 ${result.trades.length} 笔交易（${broker}）：\n\n` +
        lines.join("\n") +
        "\n\n如有误差请在多维表格中修改。";

      await replyMessage(env, message.message_id, reply);
      return new Response("OK", { status: 200 });
    } catch (e) {
      console.error("Worker error:", e);
      return new Response("OK", { status: 200 });
    }
  },
};
