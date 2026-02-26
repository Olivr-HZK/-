import json

import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

APP_ID = "cli_a9c66bf18d7a1bef"
APP_SECRET = "exDwC5SaV9I1LJ5XhwCUrbRoHEi7U5kM"
APP_TOKEN = "Qf4YbaYpvaCn9HsSdC2cdSBGnYg"
TABLE_ID = "tblpTas8AYPSWznx"

"""

# SDK 使用说明: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python--sdk/preparations-before-development
# 以下示例代码默认根据文档示例值填充，如果存在代码问题，请在 API 调试台填上相关必要参数后再复制代码使用
# 复制该 Demo 后, 需要将 "YOUR_APP_ID", "YOUR_APP_SECRET" 替换为自己应用的 APP_ID, APP_SECRET.
def main():
    # 创建client
    client = lark.Client.builder() \
        .app_id(APP_ID) \
        .app_secret(APP_SECRET) \
        .log_level(lark.LogLevel.DEBUG) \
        .build()

    # 构造请求对象
    request: CreateAppTableRequest = CreateAppTableRequest.builder() \
        .app_token("appbcbWCzen6D8dezhoCH2RpMAh") \
        .request_body(CreateAppTableRequestBody.builder()
            .table(ReqTable.builder()
                .name("数据表名称")
                .default_view_name("默认的表格视图")
                .fields([AppTableCreateHeader.builder()
                    .field_name("索引字段")
                    .type(1)
                    .build(), 
                    AppTableCreateHeader.builder()
                    .field_name("单选")
                    .type(3)
                    .ui_type("SingleSelect")
                    .property(AppTableFieldProperty.builder()
                        .options([AppTableFieldPropertyOption.builder()
                            .name("Enabled")
                            .color(0)
                            .build(), 
                            AppTableFieldPropertyOption.builder()
                            .name("Disabled")
                            .color(1)
                            .build(), 
                            AppTableFieldPropertyOption.builder()
                            .name("Draft")
                            .color(2)
                            .build()
                            ])
                        .build())
                    .build()
                    ])
                .build())
            .build()) \
        .build()

    # 发起请求
    response: CreateAppTableResponse = client.bitable.v1.app_table.create(request)

    # 处理失败返回
    if not response.success():
        lark.logger.error(
            f"client.bitable.v1.app_table.create failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: \n{json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}")
        return

    # 处理业务结果
    lark.logger.info(lark.JSON.marshal(response.data, indent=4))


"""
import argparse
import csv
import re
import sys
from pathlib import Path


def build_client(log_level):
    return (
        lark.Client.builder()
        .app_id(APP_ID)
        .app_secret(APP_SECRET)
        .log_level(log_level)
        .build()
    )

_HEADER_INVALID_CHARS = re.compile(r"[^\u4e00-\u9fffA-Za-z0-9 _-]+")


def sanitize_headers(raw_headers):
    sanitized = []
    seen = {}
    for idx, raw in enumerate(raw_headers):
        name = "" if raw is None else str(raw)
        name = name.replace("\ufeff", "")
        name = _HEADER_INVALID_CHARS.sub("", name)
        name = re.sub(r"\s+", " ", name).strip()
        if not name:
            name = f"字段{idx + 1}"
        count = seen.get(name, 0) + 1
        seen[name] = count
        if count > 1:
            name = f"{name}_{count}"
        sanitized.append(name)
    return sanitized


def sanitize_headers_ascii(raw_headers):
    sanitized = []
    seen = {}
    for idx, raw in enumerate(raw_headers):
        name = "" if raw is None else str(raw)
        name = name.replace("\ufeff", "")
        name = _HEADER_INVALID_CHARS.sub("", name)
        name = re.sub(r"\s+", " ", name).strip()
        if not name:
            name = f"Field{idx + 1}"
        count = seen.get(name, 0) + 1
        seen[name] = count
        if count > 1:
            name = f"{name}_{count}"
        sanitized.append(name)
    return sanitized


def read_csv_rows(path, encoding, delimiter):
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError("CSV is empty")
        rows_raw = list(reader)
        max_len = max(len(raw_headers), max((len(r) for r in rows_raw), default=0))
        if len(raw_headers) < max_len:
            raw_headers.extend([""] * (max_len - len(raw_headers)))
        headers = sanitize_headers_ascii(raw_headers)

        changes = [
            (str(raw).strip(), new)
            for raw, new in zip(raw_headers, headers)
            if str(raw).strip() != new
        ]
        if changes:
            preview = ", ".join(
                [f"'{raw}'->'{new}'" for raw, new in changes[:5]]
            )
            more = "" if len(changes) <= 5 else f" ...(+{len(changes) - 5} more)"
            lark.logger.info(f"header normalized: {preview}{more}")

        rows = []
        for row in rows_raw:
            if len(row) < max_len:
                row = row + [""] * (max_len - len(row))
            elif len(row) > max_len:
                row = row[:max_len]
            rows.append({headers[i]: row[i] for i in range(max_len)})
        return rows, headers


def chunked(items, size):
    for idx in range(0, len(items), size):
        yield items[idx : idx + size]


def log_api_error(action, response):
    detail = ""
    try:
        detail = json.dumps(
            json.loads(response.raw.content), indent=2, ensure_ascii=False
        )
    except Exception:
        detail = str(response.raw.content)
    lark.logger.error(
        f"{action} failed, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}, resp: {detail}"
    )


def list_records(client, app_token, table_id, field_names=None, page_size=500):
    items = []
    page_token = None
    while True:
        builder = (
            ListAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .page_size(page_size)
        )
        if page_token:
            builder = builder.page_token(page_token)
        if field_names:
            builder = builder.field_names(json.dumps(field_names, ensure_ascii=False))
        request = builder.build()
        response = client.bitable.v1.app_table_record.list(request)
        if not response.success():
            log_api_error("list records", response)
            raise RuntimeError("list records failed")
        if response.data and response.data.items:
            items.extend(response.data.items)
        if not response.data or not response.data.has_more:
            break
        page_token = response.data.page_token
    return items


def list_fields(client, app_token, table_id, page_size=500):
    items = []
    page_token = None
    while True:
        builder = (
            ListAppTableFieldRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .page_size(page_size)
        )
        if page_token:
            builder = builder.page_token(page_token)
        request = builder.build()
        response = client.bitable.v1.app_table_field.list(request)
        if not response.success():
            log_api_error("list fields", response)
            raise RuntimeError("list fields failed")
        if response.data and response.data.items:
            items.extend(response.data.items)
        if not response.data or not response.data.has_more:
            break
        page_token = response.data.page_token
    return items


def create_field(client, app_token, table_id, field_name):
    request = (
        CreateAppTableFieldRequest.builder()
        .app_token(app_token)
        .table_id(table_id)
        .request_body(AppTableField.builder().field_name(field_name).type(1).build())
        .build()
    )
    response = client.bitable.v1.app_table_field.create(request)
    if not response.success():
        log_api_error("create field", response)
        raise RuntimeError(f"create field failed: {field_name}")


def delete_field(client, app_token, table_id, field_id):
    request = (
        DeleteAppTableFieldRequest.builder()
        .app_token(app_token)
        .table_id(table_id)
        .field_id(field_id)
        .build()
    )
    response = client.bitable.v1.app_table_field.delete(request)
    if not response.success():
        log_api_error("delete field", response)
        raise RuntimeError(f"delete field failed: {field_id}")


def update_field_name(client, app_token, table_id, field_id, field_name, field_type):
    request = (
        UpdateAppTableFieldRequest.builder()
        .app_token(app_token)
        .table_id(table_id)
        .field_id(field_id)
        .request_body(
            AppTableField.builder().field_name(field_name).type(field_type).build()
        )
        .build()
    )
    response = client.bitable.v1.app_table_field.update(request)
    if not response.success():
        log_api_error("update field", response)
        raise RuntimeError(f"update field failed: {field_id}")


def sync_schema(client, app_token, table_id, csv_fields, page_size=500):
    if not csv_fields:
        raise SystemExit("CSV header is empty")

    fields = list_fields(client, app_token, table_id, page_size=page_size)
    name_to_field = {field.field_name: field for field in fields if field.field_name}
    primary = next((f for f in fields if f.is_primary), None)

    if primary and primary.field_name not in csv_fields:
        target_name = csv_fields[0]
        existing_target = name_to_field.get(target_name)
        if existing_target and not existing_target.is_primary:
            delete_field(client, app_token, table_id, existing_target.field_id)
        update_field_name(
            client, app_token, table_id, primary.field_id, target_name, primary.type
        )

    fields = list_fields(client, app_token, table_id, page_size=page_size)
    name_to_field = {field.field_name: field for field in fields if field.field_name}
    csv_set = set(csv_fields)

    for name in csv_fields:
        if name not in name_to_field:
            create_field(client, app_token, table_id, name)

    for field in fields:
        if not field.field_name:
            continue
        if field.field_name not in csv_set:
            if field.is_primary:
                continue
            delete_field(client, app_token, table_id, field.field_id)


def batch_delete_records(client, app_token, table_id, record_ids, batch_size):
    for chunk in chunked(record_ids, batch_size):
        request = (
            BatchDeleteAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .request_body(
                BatchDeleteAppTableRecordRequestBody.builder().records(chunk).build()
            )
            .build()
        )
        response = client.bitable.v1.app_table_record.batch_delete(request)
        if not response.success():
            log_api_error("batch delete", response)
            raise RuntimeError("batch delete failed")


def batch_create_records(client, app_token, table_id, records, batch_size):
    for chunk in chunked(records, batch_size):
        request = (
            BatchCreateAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .request_body(
                BatchCreateAppTableRecordRequestBody.builder().records(chunk).build()
            )
            .build()
        )
        response = client.bitable.v1.app_table_record.batch_create(request)
        if not response.success():
            log_api_error("batch create", response)
            raise RuntimeError("batch create failed")


def batch_update_records(client, app_token, table_id, records, batch_size):
    for chunk in chunked(records, batch_size):
        request = (
            BatchUpdateAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .request_body(
                BatchUpdateAppTableRecordRequestBody.builder().records(chunk).build()
            )
            .build()
        )
        response = client.bitable.v1.app_table_record.batch_update(request)
        if not response.success():
            log_api_error("batch update", response)
            raise RuntimeError("batch update failed")


def build_records(rows):
    return [AppTableRecord.builder().fields(row).build() for row in rows]


def build_key_map(records, key_field):
    mapping = {}
    for record in records:
        fields = record.fields or {}
        key_value = fields.get(key_field)
        if key_value is None:
            continue
        key_text = str(key_value).strip()
        if not key_text:
            continue
        if record.record_id:
            mapping[key_text] = record.record_id
    return mapping


def sync_replace(client, app_token, table_id, rows, batch_size, page_size):
    existing = list_records(client, app_token, table_id, page_size=page_size)
    record_ids = [item.record_id for item in existing if item.record_id]
    if record_ids:
        batch_delete_records(client, app_token, table_id, record_ids, batch_size)
    records = build_records(rows)
    if records:
        batch_create_records(client, app_token, table_id, records, batch_size)


def sync_upsert(
    client,
    app_token,
    table_id,
    rows,
    key_field,
    batch_size,
    page_size,
    delete_missing,
):
    existing = list_records(
        client, app_token, table_id, field_names=[key_field], page_size=page_size
    )
    key_map = build_key_map(existing, key_field)
    create_records = []
    update_records = []
    seen_keys = set()

    for row in rows:
        key_value = row.get(key_field)
        if key_value is None:
            continue
        key_text = str(key_value).strip()
        if not key_text:
            continue
        seen_keys.add(key_text)
        record_id = key_map.get(key_text)
        if record_id:
            update_records.append(
                AppTableRecord.builder().record_id(record_id).fields(row).build()
            )
        else:
            create_records.append(AppTableRecord.builder().fields(row).build())

    if update_records:
        batch_update_records(client, app_token, table_id, update_records, batch_size)
    if create_records:
        batch_create_records(client, app_token, table_id, create_records, batch_size)

    if delete_missing:
        missing_ids = [
            record_id for key, record_id in key_map.items() if key not in seen_keys
        ]
        if missing_ids:
            batch_delete_records(client, app_token, table_id, missing_ids, batch_size)


def parse_args():
    parser = argparse.ArgumentParser(description="Push CSV data into Feishu Bitable.")
    parser.add_argument("csv_path", type=Path, help="Path to CSV file")
    parser.add_argument(
        "--app-token",
        default=APP_TOKEN,
        help="Bitable app_token (default from APP_TOKEN)",
    )
    parser.add_argument(
        "--table-id",
        default=TABLE_ID,
        help="Bitable table_id (default from TABLE_ID)",
    )
    parser.add_argument(
        "--mode",
        choices=["replace", "upsert"],
        default="replace",
        help="replace deletes all records then inserts; upsert updates by key field",
    )
    parser.add_argument(
        "--key-field",
        default=None,
        help="Field name used as unique key for upsert mode",
    )
    parser.add_argument(
        "--delete-missing",
        action="store_true",
        help="Delete records not present in CSV (upsert mode only)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="CSV encoding",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV delimiter",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for API requests",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Page size for list records",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="SDK log level",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.app_token or not str(args.app_token).strip():
        raise SystemExit("missing app_token: set APP_TOKEN or pass --app-token")
    if not args.table_id or not str(args.table_id).strip():
        raise SystemExit("missing table_id: set TABLE_ID or pass --table-id")
    if args.mode == "upsert" and not args.key_field:
        raise SystemExit("--key-field is required for upsert mode")
    if args.delete_missing and args.mode != "upsert":
        raise SystemExit("--delete-missing requires --mode upsert")

    log_level = getattr(lark.LogLevel, args.log_level)
    client = build_client(log_level)
    rows, csv_fields = read_csv_rows(args.csv_path, args.encoding, args.delimiter)
    sync_schema(
        client,
        args.app_token,
        args.table_id,
        csv_fields,
        page_size=args.page_size,
    )

    if args.mode == "replace":
        sync_replace(
            client,
            args.app_token,
            args.table_id,
            rows,
            args.batch_size,
            args.page_size,
        )
    else:
        sync_upsert(
            client,
            args.app_token,
            args.table_id,
            rows,
            args.key_field,
            args.batch_size,
            args.page_size,
            args.delete_missing,
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        lark.logger.error(f"sync failed: {exc}")
        sys.exit(1)
