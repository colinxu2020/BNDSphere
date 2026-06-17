from pydantic import BaseModel


def requested_update_fields(payload: BaseModel) -> list[str]:
    system_fields = {
        "moderator_id",
        "moderate_at",
        "requestor_id",
        "request_at",
        "user_id",
        "club_id",
        "club_activity_id",
        "update_fields",
    }
    return sorted(payload.model_fields_set - system_fields)


def build_update_payload[SchemaType: BaseModel](
    request: object,
    schema_type: type[SchemaType],
) -> SchemaType:
    schema_fields = set(schema_type.model_fields)
    raw_fields = getattr(request, "update_fields", None)
    if isinstance(raw_fields, list) and raw_fields:
        update_fields = [field for field in raw_fields if field in schema_fields]
    else:
        update_fields = [
            field
            for field in schema_fields
            if getattr(request, field, None) is not None
        ]

    data = {field: getattr(request, field) for field in update_fields}
    return schema_type.model_validate(data)
