"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, Languages, Loader2 } from "lucide-react";
import { updateLocale } from "@/app/actions/preferences";
import { toast } from "@/lib/toast";
import type { Locale } from "@/lib/locale";

interface LanguageSettingsFormProps {
  locale: Locale;
  labels: {
    cardTitle: string;
    cardHint: string;
    english: string;
    chinese: string;
    current: string;
    apply: string;
    success: string;
  };
}

export default function LanguageSettingsForm({ locale, labels }: LanguageSettingsFormProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const options: Array<{ value: Locale; label: string }> = [
    { value: "en", label: labels.english },
    { value: "zh", label: labels.chinese },
  ];

  return (
    <div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex items-start gap-3">
        <div className="rounded-xl bg-indigo-100 p-3 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
          <Languages className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{labels.cardTitle}</h2>
          <p className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">{labels.cardHint}</p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {options.map((option) => {
          const selected = option.value === locale;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() =>
                startTransition(async () => {
                  const result = await updateLocale(option.value);
                  if (result.ok) {
                    toast.success(labels.success);
                    router.refresh();
                  }
                })
              }
              disabled={pending}
              className={`rounded-2xl border p-5 text-left transition-colors ${
                selected
                  ? "border-indigo-500 bg-indigo-50 dark:border-indigo-400 dark:bg-indigo-950/30"
                  : "border-neutral-200 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-800/50"
              }`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{option.label}</span>
                {selected ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    {labels.current}
                  </span>
                ) : null}
              </div>
              <div className="mt-4">
                <span className="inline-flex items-center gap-2 rounded-lg bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-700 dark:bg-neutral-800 dark:text-neutral-200">
                  {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Languages className="h-4 w-4" />}
                  {labels.apply}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
