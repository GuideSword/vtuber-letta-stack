### 只删除部分记忆的具体操作 1. 先查看代理ID
首先，你需要知道要操作的代理ID：

```
# 查看所有代理及其ID
sqlite3 "C:\Users\sword\.letta\sqlite.db" "SELECT id, 
name, created_at FROM agents;"
``` 2. 删除部分对话历史
查看对话历史 ：

```
# 查看特定代理的最近10条对话
sqlite3 "C:\Users\sword\.letta\sqlite.db" "SELECT id, 
role, created_at, text FROM messages WHERE agent_id = '你
的代理ID' ORDER BY created_at DESC LIMIT 10;"
```
删除特定对话 ：

```
# 根据ID删除特定对话
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE id = '对话ID';"

# 删除特定代理的特定日期之前的对话
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE agent_id = '你的代理ID' AND created_at < 
'2024-01-01';"

# 删除特定角色的对话（如只删除用户的对话）
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE agent_id = '你的代理ID' AND role = 'user';"

# 删除包含特定关键词的对话
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE agent_id = '你的代理ID' AND (text LIKE '%关
键词%' OR content LIKE '%关键词%');"
``` 3. 删除部分记忆片段
查看记忆片段 ：

```
# 查看特定代理的最近10条记忆片段
sqlite3 "C:\Users\sword\.letta\sqlite.db" "SELECT id, 
created_at, SUBSTR(text, 1, 50) AS preview FROM 
agent_passages WHERE agent_id = '你的代理ID' ORDER BY 
created_at DESC LIMIT 10;"
```
删除特定记忆片段 ：

```
# 根据ID删除特定记忆片段
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
agent_passages WHERE id = '记忆片段ID';"

# 删除特定代理的30天前的记忆片段
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
agent_passages WHERE agent_id = '你的代理ID' AND 
created_at < datetime('now', '-30 days');"

# 删除包含特定关键词的记忆片段
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
agent_passages WHERE agent_id = '你的代理ID' AND text LIKE 
'%关键词%';"
``` 4. 修改核心记忆
核心记忆存储在 block 表中，通常包含 persona 和 human 两个主要块：

查看核心记忆 ：

```
# 查看所有核心记忆块
sqlite3 "C:\Users\sword\.letta\sqlite.db" "SELECT id, 
label, value FROM block;"
```
修改核心记忆 ：

```
# 更新特定核心记忆块的内容（如清空persona块）
sqlite3 "C:\Users\sword\.letta\sqlite.db" "UPDATE block 
SET value = '' WHERE label = 'persona';"

# 部分修改核心记忆内容
sqlite3 "C:\Users\sword\.letta\sqlite.db" "UPDATE block 
SET value = REPLACE(value, '旧内容', '新内容') WHERE label 
= 'persona';"
```
### 5. 只删除特定代理的所有记忆
如果你想删除某个特定代理的所有记忆，但保留其他代理的记忆：

```
# 步骤1：停止Letta服务（如果正在运行）

# 步骤2：删除特定代理的对话历史
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE agent_id = '你的代理ID';"

# 步骤3：删除特定代理的记忆片段
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
agent_passages WHERE agent_id = '你的代理ID';"

# 步骤4：删除特定代理的核心记忆关联
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
blocks_agents WHERE agent_id = '你的代理ID';"

# 步骤5：删除特定代理的文件夹
Remove-Item -Recurse -Force "C:\Users\sword\.letta\agents\
你的代理ID"

# 步骤6：重启Letta服务
```
### 操作示例 示例1：删除最近7天的对话历史
```
# 删除特定代理最近7天的对话
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE agent_id = '你的代理ID' AND created_at > 
datetime('now', '-7 days');"
``` 示例2：删除包含敏感信息的记忆
```
# 删除包含密码的记忆片段
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
agent_passages WHERE agent_id = '你的代理ID' AND text LIKE 
'%password%' OR text LIKE '%密码%';"

# 删除包含密码的对话
sqlite3 "C:\Users\sword\.letta\sqlite.db" "DELETE FROM 
messages WHERE agent_id = '你的代理ID' AND (text LIKE 
'%password%' OR content LIKE '%密码%');"
``` 示例3：清空核心记忆中的persona
```
# 清空persona核心记忆块
sqlite3 "C:\Users\sword\.letta\sqlite.db" "UPDATE block 
SET value = '' WHERE label = 'persona';"
```
### 注意事项
1. 停止Letta服务 ：在执行删除操作前，确保Letta服务已停止，避免文件被占用。
2. 备份数据库 ：在进行任何删除操作前，建议先备份 sqlite.db 文件：
   
   ```
   Copy-Item "C:\Users\sword\.letta\sqlite.db" 
   "C:\Users\sword\.letta\sqlite.db.bak"
   ```
3. 谨慎操作 ：删除操作是不可逆的，请确保SQL语句正确无误后再执行。
4. 验证结果 ：操作完成后，重启Letta服务并检查记忆是否已正确删除。
5. 使用事务 ：对于重要的删除操作，建议使用SQL事务以确保操作的原子性。
### 完整操作流程
1. 停止Letta服务
2. 备份sqlite.db文件
3. 查看代理ID
4. 执行特定的删除命令
5. 验证删除结果
6. 重启Letta服务
如果你需要更具体的删除操作，请提供你想要删除的记忆类型和具体条件，我可以为你提供更精确的SQL命令。