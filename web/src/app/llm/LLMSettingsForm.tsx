"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Bot, Loader2, Sparkles, Save } from "lucide-react";
import { updateLLMConfig } from "@/app/actions/llm";
import { toast } from "@/lib/toast";

interface LLMConfigSection {
  base_url: string;
  api_key: string;
  model: string;
}

interface LLMConfig {
  main: LLMConfigSection;
  skill_generation: LLMConfigSection;
}

interface LLMSettingsFormProps {
  initialConfig: LLMConfig;
}

function SectionCard({
  title,
  hint,
  icon,
  values,
  onChange,
  inheritHint,
}: {
  title: string;
  hint: string;
  icon: React.ReactNode;
  values: LLMConfigSection;
  onChange: (field: keyof LLMConfigSection, value: string) => void;
  inheritHint?: string;
}) {
  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-indigo-100 p-3 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
          {icon}
        </div>
        <div>
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{title}</h2>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">{hint}</p>
          {inheritHint ? (
            <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">
              {inheritHint}
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-6 grid gap-4">
        <label className="grid gap-2 text-sm">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">Base URL</span>
          <input
            value={values.base_url}
            onChange={(e) => onChange("base_url", e.target.value)}
            className="rounded-xl border border-neutral-200 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 dark:border-neutral-800 dark:bg-neutral-950"
            placeholder="http://host.docker.internal:11434/v1"
          />
        </label>

        <label className="grid gap-2 text-sm">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">Model</span>
          <input
            value={values.model}
            onChange={(e) => onChange("model", e.target.value)}
            className="rounded-xl border border-neutral-200 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 dark:border-neutral-800 dark:bg-neutral-950"
            placeholder="glm-4.5-air / qwen2.5:14b / gpt-4o-mini"
          />
        </label>

        <label className="grid gap-2 text-sm">
          <span className="font-medium text-neutral-700 dark:text-neutral-300">API Key</span>
          <input
            type="password"
            value={values.api_key}
            onChange={(e) => onChange("api_key", e.target.value)}
            className="rounded-xl border border-neutral-200 bg-white px-4 py-3 outline-none transition focus:border-indigo-500 dark:border-neutral-800 dark:bg-neutral-950"
            placeholder="ollama / sk-... / provider token"
          />
        </label>
      </div>
    </div>
  );
}

export default function LLMSettingsForm({ initialConfig }: LLMSettingsFormProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [config, setConfig] = useState<LLMConfig>(initialConfig);

  const updateSection = (
    section: keyof LLMConfig,
    field: keyof LLMConfigSection,
    value: string,
  ) => {
    setConfig((current) => ({
      ...current,
      [section]: {
        ...current[section],
        [field]: value,
      },
    }));
  };

  const save = () => {
    startTransition(async () => {
      const result = await updateLLMConfig(config);
      if (result.error) {
        toast.error(result.error);
        return;
      }
      toast.success("LLM settings updated.");
      router.refresh();
    });
  };

  return (
    <div className="space-y-6">
      <SectionCard
        title="Main Agent LLM"
        hint="This model is used for the normal agent runtime, planning, routing escalation, and conversation responses."
        icon={<Bot className="h-5 w-5" />}
        values={config.main}
        onChange={(field, value) => updateSection("main", field, value)}
      />

      <SectionCard
        title="Skill Generation LLM"
        hint="This model is used for skill card generation and routing-example generation."
        inheritHint="Leave any field empty to inherit the corresponding value from the main agent LLM."
        icon={<Sparkles className="h-5 w-5" />}
        values={config.skill_generation}
        onChange={(field, value) => updateSection("skill_generation", field, value)}
      />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={save}
          disabled={pending}
          className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          Save Settings
        </button>
      </div>
    </div>
  );
}
