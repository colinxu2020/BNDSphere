import React, { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, RefreshCw } from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import { ClubActivitiesSection } from "./clubWorkspace/ClubActivitiesSection";
import { ClubProfileRequestSection } from "./clubWorkspace/ClubProfileRequestSection";
import { ClubRecordsSection } from "./clubWorkspace/ClubRecordsSection";
import { ClubStarApplicationsSection } from "./clubWorkspace/ClubStarApplicationsSection";
import {
  ClubHeaderSection,
  LoadErrorsSection,
  StarRatingSection,
} from "./clubWorkspace/displaySections";
import type { components } from "../api/schema";
import { PageHeader, SecondaryButton } from "../components/ui/AppPrimitives";

type Club = components["schemas"]["ClubInfo"];
type ClubActivity = components["schemas"]["ClubActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type StarApplication = components["schemas"]["StarLevelApplicationInfo"];
type StarRating = components["schemas"]["StarRatingResponse"];

export function ClubWorkspace() {
  const { id } = useParams<{ id: string }>();
  const clubId = Number(id);

  const [club, setClub] = useState<Club | null>(null);
  const [activities, setActivities] = useState<ClubActivity[]>([]);
  const [generalActivities, setGeneralActivities] = useState<GeneralActivity[]>([]);
  const [records, setRecords] = useState<ClubGeneralActivity[]>([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>([]);
  const [starRating, setStarRating] = useState<StarRating | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadErrors, setLoadErrors] = useState<Record<string, unknown>>({});

  const refresh = async () => {
    setIsLoading(true);
    const errors: Record<string, unknown> = {};

    const clubResponse = await client.GET("/api/v1/clubs/{club_id}", {
      params: { path: { club_id: clubId } },
    });
    if (clubResponse.error) {
      errors.club = clubResponse.error;
      setClub(null);
    } else {
      const nextClub = clubResponse.data || null;
      setClub(nextClub);
    }

    const activitiesResponse = await client.GET("/api/v1/clubs/{club_id}/activities/", {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (activitiesResponse.error) {
      errors.activities = activitiesResponse.error;
      setActivities([]);
    } else {
      setActivities(activitiesResponse.data?.items || []);
    }

    const generalActivitiesResponse = await client.GET("/api/v1/general-activities/", {
      params: { query: { size: 100 } },
    });
    if (generalActivitiesResponse.error) {
      errors.generalActivities = generalActivitiesResponse.error;
      setGeneralActivities([]);
    } else {
      setGeneralActivities(generalActivitiesResponse.data?.items || []);
    }

    const recordsResponse = await client.GET("/api/v1/clubs/{club_id}/general-activities/", {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (recordsResponse.error) {
      errors.records = recordsResponse.error;
      setRecords([]);
    } else {
      setRecords(recordsResponse.data?.items || []);
    }

    const applicationsResponse = await client.GET("/api/v1/clubs/{club_id}/star-level/", {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (applicationsResponse.error) {
      errors.starApplications = applicationsResponse.error;
      setStarApplications([]);
    } else {
      setStarApplications(applicationsResponse.data?.items || []);
    }

    const ratingResponse = await client.GET("/api/v1/clubs/{club_id}/star-rating/", {
      params: { path: { club_id: clubId } },
    });
    if (ratingResponse.error) {
      errors.starRating = ratingResponse.error;
      setStarRating(null);
    } else {
      setStarRating(ratingResponse.data || null);
    }

    setLoadErrors(errors);
    setIsLoading(false);
  };

  useEffect(() => {
    refresh().catch((error) => {
      setLoadErrors({ workspace: error });
      setIsLoading(false);
    });
  }, [clubId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex flex-col gap-8"
    >
      <Link
        to={`/club/${clubId}`}
        className="inline-flex items-center gap-2 text-content-muted hover:text-content font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回社团
      </Link>

      <PageHeader
        density="compact"
        eyebrow="Workspace"
        title={club?.name || `社团 #${clubId} 工作台`}
        action={
          <SecondaryButton onClick={() => refresh()} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {isLoading ? (
        <div className="animate-pulse bg-surface rounded-md h-72 border border-edge-subtle" />
      ) : (
        <>
          {Object.keys(loadErrors).length > 0 && <LoadErrorsSection errors={loadErrors} />}

          {club && <ClubHeaderSection club={club} />}

          <StarRatingSection starRating={starRating} />

          <ClubActivitiesSection clubId={clubId} activities={activities} onChanged={refresh} />

          <ClubRecordsSection
            clubId={clubId}
            generalActivities={generalActivities}
            records={records}
            onSubmitted={refresh}
          />

          <ClubStarApplicationsSection
            clubId={clubId}
            starApplications={starApplications}
            onChanged={refresh}
          />

          <ClubProfileRequestSection
            clubId={clubId}
            initialSummary={club?.summary || ""}
            initialDescription={club?.description || ""}
            initialLogo={club?.logo_uri || ""}
          />
        </>
      )}
    </motion.div>
  );
}
