"use client";

import { useState } from "react";
import { ImportWizard } from "@/components/imports/ImportWizard";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FormField } from "@/components/ui/FormField";
import { Select } from "@/components/ui/Select";
import { downloadImportTemplate } from "@/lib/api/dataImport";
import { useLocalAuth } from "@/lib/auth/useLocalAuth";
import { useCurrentBusiness } from "@/lib/business/CurrentBusinessContext";
import { IMPORT_DATA_TYPES, ImportDataType } from "@/types/dataImport";
import { useT } from "@/lib/i18n/LanguageProvider";

export default function DataUploadPage() {
  const { t, label } = useT();
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId, currentBusiness } = useCurrentBusiness();
  const canImport = currentBusiness?.role !== "viewer";
  const [dataType, setDataType] = useState<ImportDataType>("customers");
  const [isDownloading, setIsDownloading] = useState(false);

  async function handleDownloadTemplate() {
    if (!currentBusinessId) return;
    setIsDownloading(true);
    try {
      await downloadImportTemplate(getAccessToken(), currentBusinessId, dataType);
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">{t("dash.dataUpload")}</h1>

      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-56">
            <FormField label={t("s.data_type")}>
              <Select
                value={dataType}
                onChange={(e) => setDataType(e.target.value as ImportDataType)}
              >
                {IMPORT_DATA_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {label("import.type", type.value)}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button variant="secondary" onClick={handleDownloadTemplate} disabled={isDownloading}>
            {isDownloading ? t("s.downloading") : t("s.download_template")}
          </Button>
        </div>
      </Card>

      <Card>
        {currentBusinessId && !canImport ? (
          <p className="text-sm text-slate-500">
            {t("import.viewOnly")}
          </p>
        ) : currentBusinessId ? (
          <ImportWizard
            key={dataType}
            token={getAccessToken()}
            businessId={currentBusinessId}
            dataType={dataType}
          />
        ) : (
          <p className="text-sm text-slate-500">{t("import.selectBusiness")}</p>
        )}
      </Card>
    </div>
  );
}
