# Release v0.3.0-rc1 — GitHub Release 등록용 노트

**태그**: `v0.3.0-rc1`
**커밋**: `e66da2a` (main HEAD, 외부 피드백 시작 준비 머지)
**릴리즈 제목**: `v0.3.0-rc1 — Issue 1 정식 발행 준비 (5/31 목표)`
**Pre-release 표시**: ❌ OFF (Latest로 표시)
  → 외부 방문자가 GitHub 메인 페이지에서 가장 최신 release를 즉시 확인하도록. v0.2.1보다 v0.3.0-rc1이 더 정확한 현재 상태 반영.

---

## 등록 절차

### 방법 1: GitHub Web UI (권장)
1. https://github.com/shinbuheon-prog/claude-magazine/releases/new
2. **Tag** 드롭다운에서 `v0.3.0-rc1` 선택 (이미 push 완료 상태 — 아래 §"git tag 작업" 참조)
3. **Release title**: `v0.3.0-rc1 — Issue 1 정식 발행 준비 (5/31 목표)`
4. **Previous tag** = `v0.2.1` 선택 → **Generate release notes** 클릭 (자동 commit 요약)
5. **Description** 자동 생성된 노트 **위쪽**에 [reports/release_v0.3.0-rc1_body_only.md](release_v0.3.0-rc1_body_only.md) 내용 붙여넣기
6. **Set as the latest release** ✅ **체크 (ON)** — Pre-release 체크박스는 OFF
7. **Publish release** 클릭

### 방법 2: gh CLI
```bash
gh release create v0.3.0-rc1 \
  --title "v0.3.0-rc1 — Issue 1 정식 발행 준비 (5/31 목표)" \
  --notes-file reports/release_v0.3.0-rc1_body_only.md \
  --latest
```

> 주의: 본 환경에 `gh` 미설치. 방법 1 (GitHub Web UI) 권장.

---

## git tag 작업 (Claude가 사전 진행)

main HEAD `e66da2a`에 annotated tag 생성 + push:

```bash
git tag -a v0.3.0-rc1 e66da2a -m "Issue 1 정식 발행 준비 — 5월 31일 v0.3.0 목표"
git push origin v0.3.0-rc1
```

→ tag push 완료 후 GitHub Web UI의 Tag 드롭다운에서 `v0.3.0-rc1`이 즉시 노출됨.

---

## Release body (Description 필드에 복사·붙여넣기)

본 노트의 본문 부분만 [reports/release_v0.3.0-rc1_body_only.md](release_v0.3.0-rc1_body_only.md)로 분리해 GitHub UI에 붙여넣기 편하게 준비.

---

## Attach binaries 후보

- 아직 5월 호 PDF 미생성 (5/30 빌드 예정). 본 release에는 binary 미첨부
- 5/31 정식 v0.3.0 release 시점에 `output/claude-magazine-2026-05.pdf` 첨부 예정

---

## "Latest" 표시 결정 — ON 권장 (사유)

| 측면 | ON (권장) | OFF (대안) |
|---|---|---|
| 외부 방문자 명확성 | ✅ 메인 페이지에 v0.3.0-rc1 노출, "5월 호 발행 준비" 정체성 즉시 전달 | v0.2.1만 노출 → "Phase 8 closure"가 최신 상태로 잘못 인식 |
| Threads 게시 정합 | ✅ "현재 v0.2.1 closure, 5월 호 정식 발행 예정"과 일치 (rc1이 발행 준비 신호) | 게시글이 가리키는 GitHub Release와 불일치 |
| 표준 관행 | rc는 일반적으로 pre-release 표기. 단 본 매거진은 외부 피드백 우선이라 ON 정당화 가능 | rc 표기 표준 준수 |
| 6월 호 결정 영향 | v0.3.0-rc1 → v0.3.0 (5/31) → v0.3.1 (6월 호) 자연스러운 흐름 | 동상 |

→ 본 매거진은 외부 피드백 시작 + 매거진 정체성 노출 우선이라 **Latest ON 권장**.

---

## 변경 이력

- 2026-04-26: 초안 작성. v0.2.1 → v0.3.0-rc1 13 commits 정리 + Latest 표시 ON 결정.
