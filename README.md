# ⚙️ automation-scripts
데이터 엔지니어링/분석에 쓰는 **파이썬 자동화 스크립트 모음** 레포입니다.  
작고 유용한 도구들을 폴더 단위로 정리합니다.

> 목적: 반복 작업 최소화 · 분석 준비 시간 단축 · 학습/실험 기록

---

## 📦 스크립트 목록

| 스크립트명 | 설명 | 엔트리 포인트 |
|------------|------|----------------|
| `kaggle-erd-gen` | CSV를 이용하여 DBML & ERD 생성 | `kaggle-erd-gen/kaggle_to_dbml.py` |

---

## 🚀 빠른 시작
```bash
git clone https://github.com/jiminnote/automation-scripts.git
cd automation-scripts
python -V  # 3.8+
```
> 개별 스크립트의 추가 의존성이나 사용법은 각 폴더의 README.md 참고
---
## 🗂️ 폴더 구조 예시
```
automation-scripts/
  ├─ kaggle-erd-gen/
  │   ├─ examples/
  │   ├─ kaggle_to_dbml.py
  │   └─ README.md
  ├─ <next-tool>/
  │   └─ README.md
  └─ README.md  ← (현재 문서)
```
---
## 📝 변경 이력
* 2025-08-16 — kaggle-erd-gen 최초 추가
