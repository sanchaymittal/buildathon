export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const apiBase =
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000";

  const response = await fetch(`${apiBase}/deployments/quick/replace`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const payload = await response.text();
  const contentType = response.headers.get("content-type") || "application/json";

  return new Response(payload, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}
