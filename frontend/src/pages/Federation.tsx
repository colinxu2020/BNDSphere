import React, { useEffect, useState } from "react";
import { motion } from "motion/react";
import { RefreshCw } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import { useActionFeedback } from "../lib/useActionFeedback";
import type { components } from "../api/schema";
import { PageHeader, SecondaryButton, StatusMessage } from "../components/ui/AppPrimitives";
import { sortStarApplications } from "./federation/starReview";
import { ActivityEditorPanel } from "./federation/ActivityEditorPanel";
import { ActivityRequestsPanel } from "./federation/ActivityRequestsPanel";
import { ClubRecordsPanel } from "./federation/ClubRecordsPanel";
import { StarApplicationsPanel } from "./federation/StarApplicationsPanel";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type ActivityCreateRequest =
  components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest =
  components["schemas"]["ClubActivityUpdateRequestInfo"];
type StarApplication = components["schemas"]["StarLevelApplicationPublicInfo"];
type StarReviewPreview =
  components["schemas"]["StarLevelApplicationReviewPreview"];

export function Federation() {
  const [activities, setActivities] = useState<GeneralActivity[]>([]);
  const [activityCreateRequests, setActivityCreateRequests] = useState<
    ActivityCreateRequest[]
  >([]);
  const [activityUpdateRequests, setActivityUpdateRequests] = useState<
    ActivityUpdateRequest[]
  >([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>(
    [],
  );
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const feedback = useActionFeedback();

  const loadWorkspace = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [activityResponse, createResponse, updateResponse, starResponse] =
        await Promise.all([
          client.GET("/api/v1/general-activities/", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/moderations/club-activities/create-requests", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/moderations/club-activities/update-requests", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/star-level/", {
            params: { query: { size: 50 } },
          }),
        ]);

      setActivities(
        activityResponse.error ? [] : activityResponse.data?.items || [],
      );
      setActivityCreateRequests(
        createResponse.error ? [] : createResponse.data?.items || [],
      );
      setActivityUpdateRequests(
        updateResponse.error ? [] : updateResponse.data?.items || [],
      );
      setStarApplications(
        starResponse.error
          ? []
          : (starResponse.data?.items || [])
              .filter(
                (application) =>
                  application.academic_term.is_current &&
                  application.audit_status !== "approved",
              )
              .sort(sortStarApplications),
      );

      const firstError =
        activityResponse.error ||
        createResponse.error ||
        updateResponse.error ||
        starResponse.error;
      if (firstError) setLoadError(firstError);
    } catch (error) {
      setLoadError(error);
      setActivities([]);
      setActivityCreateRequests([]);
      setActivityUpdateRequests([]);
      setStarApplications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex flex-col gap-8"
    >
      <PageHeader density="compact"
        eyebrow="Federation"
        title="社联工作台"
        action={
          <SecondaryButton
            type="button"
            onClick={loadWorkspace}
            disabled={isLoading}
          >
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {feedback.message && <StatusMessage value={feedback.message} tone={feedback.tone} />}
      {loadError && <StatusMessage value={loadError} />}

      <ActivityRequestsPanel
        createRequests={activityCreateRequests}
        updateRequests={activityUpdateRequests}
        feedback={feedback}
        onModerated={loadWorkspace}
      />

      <ClubRecordsPanel
        activities={activities}
        isLoading={isLoading}
        feedback={feedback}
        onUpdated={loadWorkspace}
      />

      <StarApplicationsPanel
        applications={starApplications}
        isLoading={isLoading}
        feedback={feedback}
        onReviewed={loadWorkspace}
      />
      <ActivityEditorPanel
        activities={activities}
        isLoading={isLoading}
        feedback={feedback}
        onChanged={loadWorkspace}
      />
    </motion.div>
  );
}
