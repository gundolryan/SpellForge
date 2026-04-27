<div align="center">

# SpellForge

**맨손으로 마법을 시전한다**

MediaPipe와 OpenCV 기반 실시간 손 제스처 마법 시스템

<br/>

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-0097A7?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

</div>

---

## 소개

컨트롤러도, 버튼도 없이 오직 손만으로 마법을 시전합니다.
손바닥을 펼쳐 방패를 치고, 주먹을 쥐어 에너지를 충전하고, 검지로 겨냥해 파이어볼을 발사하세요.
게임 모드에서는 날아오는 적과 탄환을 직접 막고 격파합니다.

<br/>

<div align="center">
  <img src="https://github.com/user-attachments/assets/7bde13b2-e69f-4d39-8859-a773cdddbcac" width="700" />
</div>

---

## 마법 목록

<br/>

<div align="center">

| | 제스처 | 마법 | 설명 |
|:---:|:---:|:---:|:---|
| ✋ | 손바닥 펼치기 | **방패** | 손가락을 모두 펴서 유지하면 방어막 활성화. 게임 모드에서 적의 탄환을 막아낼 수 있음 |
| ✊ | 주먹 쥐기 | **충전** | 주먹을 쥐고 유지하면 황금 오라와 함께 에너지 충전 |
| ☝️ | 검지 겨냥 | **파이어볼** | 검지만 펴서 겨냥하고 유지하면 그 방향으로 발사. 타겟 하나에 명중 후 소멸 |
| ✊→☝️ | 충전 후 겨냥 | **메가 파이어볼** | 충전 상태에서 검지를 겨냥하면 발사. 반경 150px 내 모든 적을 동시에 폭발 |

</div>

<br/>

> **양손 동시 시전** — SpellForge는 양손을 독립적으로 인식합니다. 왼손으로 방패를 유지하면서 오른손으로 파이어볼을 발사하는 것이 동시에 가능합니다.

---

## 게임 모드 — TARGET HUNT

**G 키**로 게임 로비를 열고, 검지로 카드를 겨냥해 게임을 선택합니다.

<br/>

**진행 방식**

- 적들이 화면 가장자리에서 중앙을 향해 이동하며, 일정 간격으로 **에너지 탄**을 발사
- 파이어볼로 적을 처치하고, 방패로 날아오는 탄을 막아 목숨을 지켜야 함
- 웨이브가 오를수록 적의 속도와 발사 빈도 증가

<br/>

**점수**

| 행동 | 점수 |
|------|------|
| 파이어볼로 적 처치 | 10 × 웨이브 |
| 메가 파이어볼로 적 처치 | 20 × 웨이브 (광역) |
| 방패로 탄 막기 | 5 × 웨이브 |

<br/>

**키 조작** — `G` 로비 열기/닫기 &nbsp;|&nbsp; `R` 재시작 &nbsp;|&nbsp; `Q` 종료

---

## 동작 원리

모든 마법은 **홀드 기반 상태 머신**으로 동작합니다. 자세를 일정 시간 유지해야 발동되기 때문에, 손 모양을 바꾸는 과정에서 오인식이 발생하지 않습니다.

```
자세 감지 → 매 프레임마다 카운터 증가 → 임계값 도달 → 마법 발동
자세 해제 → 카운터 즉시 리셋
```

| 마법 | 감지 조건 | 홀드 시간 |
|------|-----------|:---------:|
| 방패 | 손가락 끝 평균 거리 > 손 크기 × 1.0 | ~0.27초 |
| 충전 | 손가락 끝 평균 거리 < 손 크기 × 0.78 | ~0.40초 |
| 파이어볼 | 검지 MCP→끝 > 0.9×, 나머지 손가락 < 0.95× | ~0.50초 |

---

## 설치

```bash
git clone https://github.com/gundolryan/SpellForge.git
cd SpellForge
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

> MediaPipe 손 랜드마크 모델 (~10MB)은 첫 실행 시 자동으로 다운로드됩니다.

**macOS 카메라 권한** — 웹캠이 열리지 않으면 시스템 설정 → 개인정보 보호 및 보안 → 카메라에서 터미널 권한을 허용하세요.

---

## 프로젝트 구조

```
SpellForge/
├── main.py              # 웹캠 루프, 렌더링, 손별 시각 처리
├── gesture_detector.py  # 방패 / 충전 / 파이어볼 홀드 상태 머신
├── effects.py           # 파이어볼 이펙트 (일반 / 메가)
├── games/
│   ├── lobby.py         # 게임 선택 로비
│   └── target.py        # TARGET HUNT 게임 모드
└── requirements.txt
```

---

## 기술 스택

**MediaPipe Hand Landmarker** — 손당 21개 랜드마크를 실시간으로 추출합니다. SpellForge는 이 좌표만으로 손 모양을 분류하며, 별도의 모델 학습 없이도 세 가지 제스처를 안정적으로 구분합니다.

```
손목(0) ── 검지: MCP(5) → PIP(6) → DIP(7) → 끝(8)
        ── 중지: MCP(9) → PIP(10) → DIP(11) → 끝(12)
        ── 약지: MCP(13) → PIP(14) → DIP(15) → 끝(16)
        ── 새끼: MCP(17) → PIP(18) → DIP(19) → 끝(20)
```

**OpenCV** — 웹캠 캡처 및 프레임별 실시간 렌더링

---

## 향후 계획

- [ ] 추가 게임 모드 (리듬 게임, 보스전, 웨이브 디펜스)
- [ ] 마법 발동 사운드 이펙트
- [ ] 추가 마법 (번개, 냉기, 바람)
- [ ] MediaPipe Model Maker를 이용한 커스텀 제스처 학습

---

<div align="center">

MIT License &nbsp;·&nbsp; made by [gundolryan](https://github.com/gundolryan)

</div>
