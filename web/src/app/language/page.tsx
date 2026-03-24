import { redirect } from "next/navigation";
import { getServerAuthContext } from "@/lib/server-auth";
import { getDictionary, getServerLocale } from "@/lib/locale";
import LanguageSettingsForm from "./LanguageSettingsForm";

export default async function LanguagePage() {
  const authContext = await getServerAuthContext();
  if (!authContext) {
    redirect("/login");
  }

  const locale = await getServerLocale();
  const dict = getDictionary(locale);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
          {dict.languagePage.title}
        </h1>
        <p className="mt-2 text-neutral-500 dark:text-neutral-400">{dict.languagePage.subtitle}</p>
      </div>

      <LanguageSettingsForm locale={locale} labels={dict.languagePage} />
    </div>
  );
}
