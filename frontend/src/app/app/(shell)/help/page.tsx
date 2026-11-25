"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useT } from "@/lib/i18n/LanguageProvider";
import { MessageKey } from "@/lib/i18n/messages";
import { useTour } from "@/lib/tour/useTour";

interface HelpTopic {
  id: string;
  title: MessageKey;
  points: MessageKey[];
}

const TOPICS: HelpTopic[] = [
  { id: "start", title: "help.start.title", points: ["help.start.1", "help.start.2", "help.start.3"] },
  { id: "sales", title: "help.sales.title", points: ["help.sales.1", "help.sales.2", "help.sales.3", "help.sales.4"] },
  { id: "gst", title: "help.gst.title", points: ["help.gst.1", "help.gst.2", "help.gst.3", "help.gst.4"] },
  { id: "udhaar", title: "help.udhaar.title", points: ["help.udhaar.1", "help.udhaar.2"] },
  { id: "purch", title: "help.purch.title", points: ["help.purch.1", "help.purch.2"] },
  { id: "exp", title: "help.exp.title", points: ["help.exp.1"] },
  { id: "inv", title: "help.inv.title", points: ["help.inv.1", "help.inv.2"] },
  { id: "cust", title: "help.cust.title", points: ["help.cust.1"] },
  { id: "pay", title: "help.pay.title", points: ["help.pay.1"] },
  { id: "rep", title: "help.rep.title", points: ["help.rep.1", "help.rep.2"] },
  { id: "ai", title: "help.ai.title", points: ["help.ai.1"] },
  { id: "team", title: "help.team.title", points: ["help.team.1", "help.team.2"] },
];

export default function HelpPage() {
  const { restart } = useTour();
  const { t } = useT();

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("help.title")}</h1>
        <Button variant="secondary" onClick={restart}>
          {t("help.tour")}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {TOPICS.map((topic) => (
          <Card key={topic.id}>
            <h2 className="mb-2 text-sm font-semibold text-slate-900">{t(topic.title)}</h2>
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
              {topic.points.map((point) => (
                <li key={point}>{t(point)}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>

      <p className="mt-6 text-sm text-slate-500">
        {t("help.more")}{" "}
        <Link href="/app/integrations" className="text-brand-600 underline">
          {t("help.integrationsLink")}
        </Link>
      </p>
    </div>
  );
}
