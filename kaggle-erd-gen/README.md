# 🗂️ Kaggle ERD Generator

CSV 데이터셋에서 자동으로 **PK/FK 후보를 추론**하고,  
DBML 스키마와 ERD 다이어그램을 생성하는 파이썬 스크립트입니다.  

---

## 📌 기능
- CSV 폴더를 읽어들여 테이블 메타데이터 추출
- **PK 후보**(단일/복합) 자동 선정
- 같은 이름의 컬럼 값 분포를 비교해 **FK 후보** 추정 (1:N, 1:1 관계)
---

## 🚀 사용법
```bash
python kaggle_to_dbml.py \
  --input {csv 모음 폴더 경로} \
  --output {schema.dbml 저장할 경로}/schema.dbml \
  --report {report.md저장할 경로}/report.md \
  --erd {erd 이미지저장할 경로}/erd.svg \
```
**예시**
```bash
python kaggle_to_dbml.py \
  --input /Users/jimin/data-engineer-study/kaggle/Brazilian_E-Commerce_Public_Dataset_by_Olist/olist \
  --output /Users/jimin/data-engineer-study/automation-scripts/kaggle-erd-gen/examples/schema.dbml \
  --report /Users/jimin/data-engineer-study/automation-scripts/kaggle-erd-gen/examples/report.md \
  --erd /Users/jimin/data-engineer-study/automation-scripts/kaggle-erd-gen/examples/erd.png
```
### 주요 옵션

| 옵션 | 설명 | 기본값 |
|------|------|---------|
| `--input` | CSV 파일이 들어 있는 폴더 (필수) | - |
| `--output` | DBML 스키마 출력 파일 | `schema.dbml` |
| `--report` | PK/FK 리포트 출력 파일 | `report.md` |
| `--erd` | ERD 이미지 파일 (svg/png 등) | 없음 |

---

## 📂 예시 출력
- **schema.dbml** → [dbdiagram.io](https://dbdiagram.io)에서 ERD 확인 가능  
- **report.md** → 각 테이블별 PK/FK 추론 결과  
- **erd.svg** → 자동 생성된 ERD 다이어그램  

---

## ⚙️ 요구사항
- Python 3.8+
- pandas
- graphviz (선택, ERD 다이어그램용)
---

## ✨ 활용 예시

캐글과 같은 복잡한 CSV 기반 데이터셋을 다룰 때,  
PK/FK 값이 명시되어 있지 않더라도  
데이터 분석 전에 **테이블 구조를 빠르게 파악**하는 용도로 활용할 수 있습니다.