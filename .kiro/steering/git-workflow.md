---
inclusion: always
---

# Git Workflow - Face-Auth IdP System

このドキュメントは、Face-Auth IdP システムのGitワークフローとコミット規約を定義します。

## ブランチ戦略

### メインブランチ

#### main
- **用途:** 本番環境用（安定版）
- **保護:** 直接pushは禁止
- **マージ:** Pull Request経由のみ
- **デプロイ:** 本番環境に自動デプロイ（CI/CD）

#### develop
- **用途:** 開発環境用（統合ブランチ）
- **保護:** 直接pushは推奨しない
- **マージ:** Pull Request経由を推奨
- **デプロイ:** 開発環境に自動デプロイ

### 作業ブランチ

#### feature/* - 新機能開発
```bash
# ブランチ作成
git checkout develop
git pull origin develop
git checkout -b feature/face-login-handler

# 作業後
git add .
git commit -m "feat(lambda): Add face login handler"
git push origin feature/face-login-handler

# Pull Request作成 → develop へマージ
```

**命名規則:**
- `feature/short-description`
- 例: `feature/cognito-integration`, `feature/error-handling`

#### bugfix/* - バグ修正
```bash
# ブランチ作成
git checkout develop
git checkout -b bugfix/fix-timeout-issue

# 作業後
git commit -m "fix(timeout): Fix AD connection timeout handling"
git push origin bugfix/fix-timeout-issue
```

**命名規則:**
- `bugfix/short-description`
- 例: `bugfix/fix-liveness-detection`, `bugfix/session-expiry`

#### hotfix/* - 緊急修正（本番）
```bash
# mainから直接作成
git checkout main
git checkout -b hotfix/critical-security-fix

# 修正後、mainとdevelopの両方にマージ
git checkout main
git merge hotfix/critical-security-fix
git checkout develop
git merge hotfix/critical-security-fix
```

**命名規則:**
- `hotfix/short-description`
- 例: `hotfix/security-patch`, `hotfix/api-gateway-fix`

---

## コミットメッセージ規約

### フォーマット

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type（必須）

| Type | 説明 | 例 |
|------|------|-----|
| `feat` | 新機能 | `feat(lambda): Add face login handler` |
| `fix` | バグ修正 | `fix(timeout): Fix AD connection timeout` |
| `docs` | ドキュメント変更 | `docs: Update deployment guide` |
| `style` | コードフォーマット | `style: Format Python code with black` |
| `refactor` | リファクタリング | `refactor(service): Simplify error handling` |
| `test` | テスト追加・修正 | `test: Add unit tests for OCR service` |
| `chore` | ビルド・設定変更 | `chore: Update dependencies` |
| `perf` | パフォーマンス改善 | `perf(lambda): Optimize image processing` |
| `ci` | CI/CD変更 | `ci: Add GitHub Actions workflow` |
| `revert` | コミット取り消し | `revert: Revert "feat: Add feature X"` |

### Scope（オプション）

コミットの影響範囲を示す。

**例:**
- `lambda` - Lambda関数
- `infrastructure` - CDKインフラ
- `service` - 共有サービス
- `test` - テスト
- `docs` - ドキュメント
- `config` - 設定ファイル

### Subject（必須）

- 50文字以内
- 命令形を使用（"Add" not "Added"）
- 最初の文字は大文字
- 末尾にピリオドなし

**Good:**
```
feat(lambda): Add face login handler with 1:N matching
fix(timeout): Fix AD connection timeout handling
docs: Update infrastructure architecture document
```

**Bad:**
```
added new feature
Fixed bug.
updated docs
```

### Body（オプション）

- 72文字で改行
- 何を変更したか、なぜ変更したかを説明
- 箇条書きを使用可能

**例:**
```
feat(lambda): Add face login handler with 1:N matching

Implement complete face-based login workflow:
- Liveness detection with >90% confidence threshold
- 1:N face search in Rekognition collection
- Session creation with Cognito
- Failed login attempt storage in S3
- DynamoDB last_login update

This completes Task 8.3 of the implementation plan.
```

### Footer（オプション）

- Issue番号の参照
- Breaking changes の記載

**例:**
```
Closes #123
Fixes #456

BREAKING CHANGE: API endpoint structure changed
```

---

## コミット例

### 新機能追加
```
feat(lambda): Add emergency authentication handler

Implement emergency login with ID card + AD password:
- OCR extraction from ID card
- AD password verification with 10s timeout
- Rate limiting using DynamoDB
- Session creation with Cognito

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
Closes #45
```

### バグ修正
```
fix(cognito): Fix session expiration handling

- Add proper TTL validation in session check
- Handle expired tokens gracefully
- Return 401 instead of 500 for expired sessions

Fixes #78
```

### ドキュメント更新
```
docs: Add infrastructure architecture documentation

- VPC and network configuration details
- Lambda deployment in Private Subnet
- Security group configurations
- Public accessibility analysis
- Cost optimization strategies
```

### リファクタリング
```
refactor(service): Simplify error handler logic

- Extract common error response generation
- Reduce code duplication
- Improve type hints
- Add more comprehensive docstrings

No functional changes.
```

### テスト追加
```
test: Add integration tests for session management

- Test complete session lifecycle
- Test session expiration handling
- Test multiple sessions per user
- Test TTL format for DynamoDB

Coverage increased from 85% to 92%.
```

---

## 自動コミット（Kiro Hook）

### 設定

Kiro Hookによる自動コミットが有効化されています。

**Hook:** `.kiro/hooks/auto-commit-on-task.kiro.hook`

**トリガー:** agentStop（エージェント実行完了時）

**動作:**
```bash
git add .
git commit -m "Auto-commit: Task completed"
```

### 自動コミット後の推奨作業

1. **コミットメッセージの修正**
```bash
# 直前のコミットメッセージを修正
git commit --amend

# エディタで詳細なメッセージに変更
feat(lambda): Add re-enrollment handler

- Implement identity verification (OCR + AD)
- Delete old face from Rekognition
- Index new face
- Update DynamoDB record
- Add audit logging

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
```

2. **複数の自動コミットをまとめる**
```bash
# 直近3つのコミットをまとめる
git rebase -i HEAD~3

# エディタで "pick" を "squash" に変更
```

---

## Pull Request（PR）ガイドライン

### PR作成前チェックリスト

- [ ] すべてのテストが通過
- [ ] コーディング規約に準拠
- [ ] ドキュメントが更新されている
- [ ] コミットメッセージが適切
- [ ] 不要なファイルが含まれていない

### PRタイトル

コミットメッセージと同じ形式を使用。

**例:**
```
feat(lambda): Add face login handler with 1:N matching
fix(timeout): Fix AD connection timeout handling
docs: Update deployment guide
```

### PR説明テンプレート

```markdown
## 概要
このPRの目的を簡潔に説明

## 変更内容
- 変更点1
- 変更点2
- 変更点3

## テスト
- [ ] 単体テスト追加
- [ ] 統合テスト実行
- [ ] 手動テスト完了

## スクリーンショット（該当する場合）
画像を添付

## 関連Issue
Closes #123
Related to #456

## チェックリスト
- [ ] コーディング規約準拠
- [ ] ドキュメント更新
- [ ] テスト追加
- [ ] Breaking changesなし（またはドキュメント化済み）
```

### レビュー観点

1. **機能性**
   - 要件を満たしているか
   - エッジケースを考慮しているか

2. **コード品質**
   - 命名規則に従っているか
   - Type hintsとdocstringsがあるか
   - 適切なエラーハンドリングがあるか

3. **テスト**
   - テストが含まれているか
   - テストカバレッジは十分か

4. **セキュリティ**
   - 機密情報の漏洩がないか
   - 適切な権限設定か

5. **パフォーマンス**
   - タイムアウト制限を守っているか
   - 不要なAPI呼び出しがないか

---

## Git コマンド集

### 基本操作

```bash
# 現在の状態確認
git status

# 変更内容確認
git diff

# ステージング
git add <file>
git add .

# コミット
git commit -m "feat: Add new feature"

# プッシュ
git push origin <branch-name>

# プル
git pull origin <branch-name>
```

### ブランチ操作

```bash
# ブランチ一覧
git branch
git branch -a  # リモートブランチも表示

# ブランチ作成
git checkout -b feature/new-feature

# ブランチ切り替え
git checkout develop

# ブランチ削除
git branch -d feature/completed-feature
git push origin --delete feature/completed-feature
```

### コミット修正

```bash
# 直前のコミットメッセージ修正
git commit --amend

# 直前のコミットに変更を追加
git add <file>
git commit --amend --no-edit

# コミット取り消し（変更は保持）
git reset --soft HEAD~1

# コミット取り消し（変更も破棄）
git reset --hard HEAD~1
```

### 履歴確認

```bash
# コミット履歴
git log
git log --oneline
git log --graph --oneline --all

# 特定ファイルの履歴
git log -- <file>

# 変更内容の詳細
git show <commit-hash>
```

### マージとリベース

```bash
# マージ
git checkout develop
git merge feature/new-feature

# リベース
git checkout feature/new-feature
git rebase develop

# コンフリクト解決後
git add <resolved-files>
git rebase --continue
```

### スタッシュ

```bash
# 変更を一時保存
git stash

# スタッシュ一覧
git stash list

# スタッシュを適用
git stash apply
git stash pop  # 適用後に削除

# スタッシュ削除
git stash drop
git stash clear  # すべて削除
```

---

## .gitignore

プロジェクトの`.gitignore`ファイルには以下が含まれています：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Virtual Environment
venv/
env/
ENV/

# PyTest
.pytest_cache/
.coverage
htmlcov/

# AWS
.aws-sam/
cdk.out/
*.zip

# IDE
.vscode/
.idea/
*.swp

# Environment variables
.env
.env.local
.env.development
.env.staging
.env.production

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
*.tmp
temp/
tmp/
```

---

## トラブルシューティング

### コンフリクト解決

```bash
# 1. コンフリクトが発生
git merge feature/branch
# CONFLICT (content): Merge conflict in file.py

# 2. コンフリクトファイルを編集
# <<<<<<< HEAD
# 現在のブランチの内容
# =======
# マージしようとしているブランチの内容
# >>>>>>> feature/branch

# 3. 解決後
git add file.py
git commit -m "fix: Resolve merge conflict"
```

### 間違ったブランチにコミット

```bash
# 1. コミットを取り消し（変更は保持）
git reset --soft HEAD~1

# 2. 正しいブランチに切り替え
git checkout correct-branch

# 3. 再度コミット
git add .
git commit -m "feat: Add feature"
```

### プッシュ済みコミットの修正

```bash
# ⚠️ 注意: 他の人がプルしている場合は避ける

# 1. コミット修正
git commit --amend

# 2. 強制プッシュ
git push origin branch-name --force-with-lease
```

---

## ベストプラクティス

### DO（推奨）

✅ **小さく頻繁にコミット**
- 論理的な単位でコミット
- 1つのコミットで1つの変更

✅ **意味のあるコミットメッセージ**
- 何を変更したか明確に
- なぜ変更したか説明

✅ **プッシュ前にテスト実行**
```bash
python -m pytest tests/ -v
```

✅ **ブランチを最新に保つ**
```bash
git checkout develop
git pull origin develop
git checkout feature/my-feature
git rebase develop
```

✅ **コードレビューを受ける**
- Pull Requestを作成
- レビューを待つ
- フィードバックに対応

### DON'T（非推奨）

❌ **大きすぎるコミット**
- 複数の機能を1つのコミットに含めない

❌ **曖昧なコミットメッセージ**
```bash
# Bad
git commit -m "fix"
git commit -m "update"
git commit -m "changes"
```

❌ **mainへの直接プッシュ**
```bash
# Bad
git checkout main
git commit -m "feat: Add feature"
git push origin main
```

❌ **機密情報のコミット**
```bash
# Bad
git add .env
git commit -m "Add config"
```

❌ **テスト失敗状態でのプッシュ**
```bash
# Bad
# テストが失敗しているのにプッシュ
git push origin feature/broken-feature
```

---

## 参考資料

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Atlassian Git Tutorials](https://www.atlassian.com/git/tutorials)

---

**最終更新:** 2024
**バージョン:** 1.0
