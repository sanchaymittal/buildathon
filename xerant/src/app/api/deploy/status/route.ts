export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const deployId = searchParams.get("deploy_id");
  const userId = searchParams.get("user_id");

  if (!deployId) {
    return new Response(
      JSON.stringify({ detail: "deploy_id is required" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  const apiBase =
    process.env.INTERNAL_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    "http://localhost:8000";

  const query = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  const response = await fetch(`${apiBase}/deployments/${deployId}${query}`);
  const payload = await response.text();
  const contentType = response.headers.get("content-type") || "application/json";

  return new Response(payload, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
    },
  });
}
