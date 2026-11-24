"use client";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useT } from "@/lib/i18n/LanguageProvider";
import { useTour } from "@/lib/tour/useTour";

export function GuidedTour() {
  const { isOpen, stepIndex, steps, next, back, skip } = useTour();
  const { t } = useT();

  const step = steps[stepIndex];
  if (!isOpen || !step) return null;

  const isLast = stepIndex === steps.length - 1;
  const isFirst = stepIndex === 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <Card className="w-full max-w-md">
        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-brand-600">
          {t("tour.step", { n: stepIndex + 1, total: steps.length })}
        </p>
        <h2 className="mb-2 text-lg font-semibold">{t(step.title)}</h2>
        <p className="mb-6 text-sm text-slate-600">{t(step.body)}</p>

        <div className="flex items-center justify-between">
          <button type="button" onClick={skip} className="text-sm text-slate-400 hover:text-slate-600">
            {t("tour.skip")}
          </button>
          <div className="flex gap-2">
            {!isFirst && (
              <Button variant="secondary" onClick={back}>
                {t("tour.back")}
              </Button>
            )}
            <Button onClick={isLast ? skip : next}>{isLast ? t("tour.finish") : t("tour.next")}</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
