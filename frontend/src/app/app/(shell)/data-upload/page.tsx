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

export default function DataUploadPage() {
  const { getAccessToken } = useLocalAuth();
  const { currentBusinessId } = useCurrentBusiness();
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
      <h1 className="mb-6 text-2xl font-semibold">Data Upload Centre</h1>

      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-56">
            <FormField label="Data type">
              <Select
                value={dataType}
                onChange={(e) => setDataType(e.target.value as ImportDataType)}
              >
                {IMPORT_DATA_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>
          <Button variant="secondary" onClick={handleDownloadTemplate} disabled={isDownloading}>
            {isDownloading ? "Downloading..." : "Download template"}
          </Button>
        </div>
      </Card>

      <Card>
        {currentBusinessId ? (
          <ImportWizard
            key={dataType}
            token={getAccessToken()}
            businessId={currentBusinessId}
            dataType={dataType}
          />
        ) : (
          <p className="text-sm text-slate-500">Select a business to import data.</p>
        )}
      </Card>
    </div>
  );
}
