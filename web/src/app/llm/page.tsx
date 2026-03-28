import { redirect } from "next/navigation";
import { buildBearerHeaders, getServerAuthContext } from "@/lib/server-auth";
import LLMSettingsForm from "./LLMSettingsForm";

interface LLMConfigSection {
  base_url: string;
  api_key: string;
  model: string;
}

interface LLMConfig {
  main: LLMConfigSection;
  skill_generation: LLMConfigSection;
}

async function getLLMConfig(token: string): Promise<LLMConfig> {
  const baseUrl = process.env.API_URL || "http://127.0.0.1:8000/api";
  const response = await fetch(`${baseUrl}/admin/llm-config`, {
    headers: buildBearerHeaders(token),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch LLM config: ${response.statusText}`);
  }

  return response.json();
}

export default async function LLMPage() {
  const authContext = await getServerAuthContext();
  if (!authContext) {
    redirect("/login");
  }

  const { token, payload } = authContext;
  if (payload.role !== "admin") {
    redirect("/dashboard");
  }

  const config = await getLLMConfig(token);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
          LLM Settings
        </h1>
        <p className="mt-2 text-neutral-500 dark:text-neutral-400">
          Configure the main agent model and the dedicated model used for skill and routing-example generation.
        </p>
      </div>

      <LLMSettingsForm initialConfig={config} />
    </div>
  );
}
