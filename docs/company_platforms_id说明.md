# company_platforms 表 id 字段分配说明

## 📋 id 字段定义

在 `company_platforms` 表中，`id` 字段的定义是：

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT
```

## 🔢 分配机制

### 1. 自动分配（AUTOINCREMENT）

`id` 字段使用 **AUTOINCREMENT** 机制，这意味着：

- ✅ **自动递增**：每次插入新记录时，如果没有指定 `id`，SQLite 会自动分配一个比当前最大 `id` 更大的整数
- ✅ **从 1 开始**：第一条记录的 `id` 是 1，第二条是 2，以此类推
- ✅ **不重用已删除的 id**：如果删除了某条记录，被删除的 `id` 不会被重新分配给新记录

### 2. 插入时的处理

在代码中，插入新记录时**不指定 `id` 字段**：

```python
conn.execute("""
    INSERT INTO company_platforms (
        company_name, game_name, platform_type, username, url,
        user_id, page_id, channel_id, handle, sec_uid, enabled, priority,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (...))
```

**注意**：插入语句中没有包含 `id` 字段，所以 SQLite 会自动分配。

### 3. 更新时的处理

当更新已存在的记录时，使用 `UPDATE` 语句，**不会改变 `id`**：

```python
conn.execute("""
    UPDATE company_platforms SET
        username = ?,
        url = ?,
        ...
    WHERE id = ?
""", (..., existing_id))
```

**注意**：更新时使用 `WHERE id = ?` 来定位记录，`id` 保持不变。

## 📊 示例

### 场景 1: 正常插入

```sql
-- 第一次插入
INSERT INTO company_platforms (...) VALUES (...);
-- id = 1

-- 第二次插入
INSERT INTO company_platforms (...) VALUES (...);
-- id = 2

-- 第三次插入
INSERT INTO company_platforms (...) VALUES (...);
-- id = 3
```

### 场景 2: 删除记录后插入

```sql
-- 当前有 id = 1, 2, 3 的记录

-- 删除 id = 2 的记录
DELETE FROM company_platforms WHERE id = 2;

-- 插入新记录
INSERT INTO company_platforms (...) VALUES (...);
-- id = 4（不是 2，因为 AUTOINCREMENT 不会重用已删除的 id）
```

### 场景 3: 更新记录

```sql
-- 更新 id = 1 的记录
UPDATE company_platforms SET url = '...' WHERE id = 1;
-- id 仍然是 1，不会改变
```

## 🔍 实际行为

### AUTOINCREMENT vs PRIMARY KEY

| 特性 | `PRIMARY KEY` | `PRIMARY KEY AUTOINCREMENT` |
|------|---------------|----------------------------|
| 自动分配 id | ✅ | ✅ |
| 重用已删除的 id | ✅（可能） | ❌（不会） |
| 性能 | 更快 | 稍慢（需要维护内部计数器） |
| 使用场景 | 一般场景 | 需要 id 永不重用的场景 |

### 为什么使用 AUTOINCREMENT？

使用 `AUTOINCREMENT` 的好处：
- ✅ **id 永不重用**：即使删除记录，`id` 也不会被重新分配给新记录
- ✅ **可追溯性**：可以通过 `id` 追踪记录的创建顺序
- ✅ **避免冲突**：在多线程/多进程环境下更安全

## 💡 注意事项

### 1. id 是内部标识符

`id` 字段主要用于：
- 数据库内部唯一标识每条记录
- 更新和删除操作时的定位
- **不是业务逻辑的一部分**

### 2. 业务去重不依赖 id

代码中的去重逻辑**不依赖 `id`**，而是基于：
- `company_name`（公司名）
- `game_name`（游戏名，NULL 视为一致）
- `platform_type`（平台类型）

```python
# 去重查询（不依赖 id）
if game_name:
    cursor = conn.execute("""
        SELECT id, created_at FROM company_platforms
        WHERE company_name = ? AND game_name = ? AND platform_type = ?
    """, (company, game_name, platform_type))
```

### 3. id 可能不连续

由于 `AUTOINCREMENT` 不会重用已删除的 `id`，所以：
- 如果删除了某些记录，`id` 序列会出现"空洞"
- 例如：1, 2, 3, 5, 6, 9（缺少 4, 7, 8）
- **这是正常现象**，不影响功能

## 🔧 查看当前 id 分配情况

### SQL 查询示例

```sql
-- 查看所有记录的 id
SELECT id, company_name, game_name, platform_type 
FROM company_platforms 
ORDER BY id;

-- 查看当前最大 id
SELECT MAX(id) as max_id FROM company_platforms;

-- 查看 id 的分布情况
SELECT 
    MIN(id) as min_id,
    MAX(id) as max_id,
    COUNT(*) as total_count,
    MAX(id) - COUNT(*) as gaps
FROM company_platforms;
```

### 检查 id 空洞

```sql
-- 查找 id 序列中的空洞
WITH RECURSIVE seq(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < (SELECT MAX(id) FROM company_platforms)
)
SELECT seq.n as missing_id
FROM seq
LEFT JOIN company_platforms ON seq.n = company_platforms.id
WHERE company_platforms.id IS NULL;
```

## 📝 总结

1. **id 分配方式**：SQLite 自动分配，使用 `AUTOINCREMENT` 机制
2. **起始值**：从 1 开始，每次插入自动递增
3. **不重用**：已删除的 `id` 不会被重新分配
4. **用途**：主要用于数据库内部标识，不参与业务逻辑去重
5. **可能不连续**：删除记录后，`id` 序列可能出现"空洞"，这是正常现象

---

**关键点**：`id` 是数据库内部使用的唯一标识符，业务逻辑的去重和匹配不依赖 `id`，而是基于公司名、游戏名和平台类型的组合。
