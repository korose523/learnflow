# M3 한글 메타데이터 내보내기 (Korean Metadata Export)

> 용도: 영산대학교 학위/연구 시스템 또는 한국어 학술 투고용 메타데이터.
> 원고 본문은 현재 중국어(및 영문 Abstract 병기)이며, 본 파일은 **서지·초록의 한글화**만 제공한다.
> 본문 전체 영문 번역·압축은 대상 저널(TLT/IJAIED) 결정 후 별도 작업 필요.

---

## 1. 저자 (Authors)

| 역할 | 성명(영문) | 성명(한글) | 소속 | ORCID |
|---|---|---|---|---|
| 제1저자 | Zexiao Weng | 웡 자샤오 | ① 영산대학교 대학원 컴퓨터정보공학과, 부산 48015, 대한민국 | 0009-0009-8600-8954 |
| 교신저자(*) | *(최종고 승인 보류)* | *( ditto )* | ① 영산대학교(부산, 대한민국) | *(최종고 승인 보류)* |

- ① Department of Computer and Information Engineering, Graduate School, Youngsan University, Busan 48015, Republic of Korea
- 교신저자 E-mail / ORCID: **최종고 승인 후 기재** (아래 说明 참조)

> **〔필자란 보류 — 심사 2.4③ 및 §10, 2026-09-29〕**
> 이 원고는 공동저자 2인 저작물이나, 필자판이 최종고를 읽고 승인하기 전까지는
> **필자란·通讯作者란(성명·이메일·ORCID)**, **Zenodo 기여자 명단**, **AI 사용 공개문** —
> 이 세 곳에 제2저자의 이름·연락처를 싣지 않는다. 제2저자는 교신저자 역할을 승낙한 상태이며,
> 최종고 승인 후 당사자가 동의하는 방식으로 복원한다. 이는 `docs/M3_submission_EN.md`
> 1부 저자란 및 「Byline and corresponding-author fields withheld pending approval」 조항과 동일한 처리다.
> (English: the second author's name, email and ORCID are withheld from the byline, the Zenodo
> contributor list and the AI-use statement until the final manuscript is approved.)

## 2. 제목 (Title)

- **한글**: 정렬된 난이도 결정과 단일 대규모언어모델(LLM) 난이도 사전의 신뢰성 경계
- **영문(원본)**: Ordered Difficulty Decisions and the Reliability Boundary of a Single Large Model's Difficulty Prior
- **중문(원본)**: 有序难度决策与单一大模型难度先验的可靠性边界

## 3. 초록 (Abstract — 한국어)

본 연구는 적응형 학습의 두 핵심 의사결정—'다음 문제의 난이도 선택'과 '난이도 사전의 출처'—이 각각 검증되지 않은 전제에 의존한다는 점에서 출발한다. 전자는 난이도 수준 간 기대 이득이 상호 무상관이라고, 후자는 대규모 언어모델(LLM)의 오프라인 난이도 주석이 온라인 의사결정의 신뢰할 수 있는 사전으로 쓰일 수 있다고 가정한다. 우리는 이 두 전제를 측정 가능한 경험적 명제로 바꾸어 네 개의 공개 학습 로그에서 실측 결과를 보고한다.

첫째, 자체 구축 시뮬레이터의 등간선형 난이도 가정 `linspace(-2,2,10)`을 Junyi Academy의 16,217,311건의 상호작용(사용자 72,758명, 연습 1,326개, CC BY-NC-SA 4.0)으로 대체하여, 동일 지식 가닥 내에서 전문가 난이도별로 묶은 실제 연습으로 행동 공간을 재구성하였다. 전문가 난이도 라벨의 경험적 성공률은 엄격히 단조(상 0.7355 / 중 0.6328 / 하 0.6160)이며, 순서 전이는 12.3퍼센트포인트의 '등반 마찰'(하→상 0.7534 > 상→상 0.7335, 상→하 0.6302)을 보여 '행동 공간이 순위형이며 전이가 비대칭'이라는 모델링 전제에 직접적인 행동 증거를 제공한다.

둘째, 52,733명의 사용자를 보정한 실제 팔(real-arm) 실험(시뮬레이션 500회 × T=40)에서 능력 사전이 옳은 정책은 0.7023, 사전이 뒤집힌 정책은 0.6714를 얻어 능력 오판의 비용이 견고하게 양(+)이었으며, **어떤 능력 사전도 필요로 하지 않는** `flow_zone` 정책은 0.7119를 얻어 능력 인지 정책과의 차이가 약 1σ(유의하지 않음)에 불과하였다. 이는 M1이 assist09에서 찾은 '단일값 최빈값(성공률 75%)'을 능력 추정 없이 실행 가능한 정렬 규칙으로 조작화한 것이다.

셋째, 본 연구는 단일 로컬 배포 모델(Qwen3.6-35B-A3B, GGUF IQ3_S)에서 LLM 난이도 사전의 신뢰성을 측정하였다. DBE-KT22의 212문항에서 앵커 척도 절대 평가는 Spearman ρ = 0.2195(p = 0.0013), 일괄 순위 + Bradley-Terry는 ρ = 0.1808(p = 0.0083)로, 둘 다 행동 증거의 전문가 라벨 일치도(ρ = 0.2207)와 동일한 수준이며 **양자 간 통계적으로 유의한 차이가 없다**(문항 수준 쌍대 부트스트랩 Δ = 0.0385, 95% CI [−0.0652, 0.2193], 양측 p = 0.34). 반면 XES3G5M의 120문항 중국어 초등 수학문제에서는 ρ = −0.038로 유의하지 않았다. 본 연구의 주장은 §5.8에서 측정한 4개 모델 계통 × 3개 규모 등급(11개 EVALUATED 셀, F4_DeepSeek 포함, 게이트 종료 코드 0으로 재현 가능)의 로컬 개방 가중치 행렬로 그 재현성을 확장하되, 그 행렬이 포괄하는 4계통 3등급(및 F4_DeepSeek)에 한정하며 모든 LLM에 대한 일반적 경계 주장으로 확대하지 않는다.

넷째, 본 연구는 난이도 추정을 정렬 의사결정에 되연결하여, 냉시작(cold-start) 정렬의 이득이 판정·표본 크기·신호 방향 검증에 강하게 의존함을 발견하였다. 풀 내(in-pool) 기준에서 전문가 라벨을 판정으로 삼은 다중 신호 융합 이득은 극소 표본(k = 10)에서만 양(+0.0271)이고 k ≥ 25부터는 전면 음전환(k = 500에서 −0.0695)된다. 방향성 오구성(승급률과 난이도의 풀 내 상관 −0.756이 +0.154의 정가중치로 최적화됨)을 찾아 제거한 뒤, 표본 크기 적응형 수축 λ*(k) = 1/(1+(k/27.3)^0.895)는 k = 10에서 풀 내 이득 +6.447pp를 주지만 k ≥ 250에서 ≤0.35pp로 감쇠한다. '보지 못한 표본의 실제 수행' 판정으로 바꾸면 동일 융합이 전면 음전환(Junyi −0.0267 ~ −0.1222, DBE −0.1752 ~ −0.2113, 융합 승리율 0.00)되므로, **본 연구는 O4/O5의 일치성 이득을 예측력 이득으로 기술하지 않는다.** 유출 검증의 완전한 수치와 학생 수준 유출(사용자 72,758명의 배타적 이분, 연습 1,238개) 및 추정기 수준의 부호 보정·반분 신뢰도 가중(srw7)은 자매 논문 M1의 7.2–7.8절에서 표로 보고되고, 본 연구는 정렬 의사결정 측의 풀 내 결과(표 6, 표 7)와 그로부터 유도된 설계 판단만을 보존한다. 위 설계 판단 중 두 항목은 본 연구의 소속 시스템 백엔드 코드에 적재되어 14건의 회귀 테스트와 외부 검증 스크립트 `o11_land_verify.py`(15/15 PASS)를 통과하였다. **본 연구의 핵심 결론은 '일치성 이득 ≠ 예측력 이득'이다.**

## 4. 키워드 (Keywords — 한국어)

순위형 행동 공간; Lipschitz 밴딧; 몰입 채널; 인출 가능성; 순차 의사결정; 단일모델 LLM 난이도 주석; 냉시작 정렬; 부정적 결과

> 영문 키워드(원본): ordinal action space; Lipschitz bandits; flow channel; retrievability; sequential decision making; single-model LLM difficulty annotation; cold-start sequencing; negative results

## 5. 한글 서지 정보 (Korean Bibliographic Suggestion)

> Weng, Z., & Jung, M. (2026). *정렬된 난이도 결정과 단일 대규모언어모델(LLM) 난이도 사전의 신뢰성 경계* [Ordered Difficulty Decisions and the Reliability Boundary of a Single Large Model's Difficulty Prior]. 영산대학교 대학원. 
> **〔교저자 표기 범위 — 심사 2.4③, 2026-09-29〕** M3은 공동저자 2인 저작물이며, 위 서지条目는 저자身份的 기록이므로 이 이름이 남는다. 심사 2.4③이 보류하는 것은 **① 원고 필자란·通讯作者란, ② Zenodo 기여자 명단, ③ AI 사용 공개문** — 이 세 곳이다. 두 번째 저자는 최종고를 읽고 승인하기 전까지 위 세 곳에 이름을 싣지 않으며, 승인 후 당사자가 동의하는 방식으로 복원한다. (학위/투고 구분은 실제 출판 형태에 따라 확정)

## 6. 데이터·코드 가용성 (Data/Code Availability — 투고 전 필수)

- 아티팩트(코드·재현 스크립트): Zenodo DOI 10.5281/zenodo.22719229 **〔아카이브 식별자 안내〕** 이 DOI는 v0.1.0(2026-09-11)이며 Zenodo 기록 제목이 「학습중독 측정도구」로, 본 연구 주선(난이도의 측정·거버넌스)과 일치하지 않습니다. 난이도 주선으로 고친 v0.2.0 메타데이터는 `.zenodo.json`에 준비되어 있고, **새 버전 공개 시 순환합니다.** 그 전까지는 저장소 README와 `CITATION.cff`를 기준으로 인용합니다. (This DOI is v0.1.0, whose Zenodo record title is a learning-addiction measurement tool, unrelated to this paper's difficulty line of work; the corrected v0.2.0 metadata is prepared and the issue closes once the new version is published.)
- 데이터셋许可: Junyi(CC BY-NC-SA 4.0 + Chang et al. 2015), DBE(DOI 10.26193/6DZWOH + arXiv:2208.12651), XES3G5M(MIT + Liu et al. NeurIPS 2023), ASSISTments 2009-2010(데이터 페이지 URL)
- AI 사용 공개: 본 연구 방법은 LLM 난이도 주석 파이프라인(단일 정적 모델 `qwen36:latest`, 기저 Qwen3.6-35B-A3B, IQ3_S)에 의존하며, 이는 IEEE(2024-04) 및 Springer Nature 정책에 따라 Methods/Acknowledgements에 명시 공개 필요. AI는 저자로 등재 불가.

---
*본 한글 메타데이터는 영문/중문 원본(및 §1.4 기여 R1–R5, §5.4–5.6 실측 수치)을 근거로 작성되었으며, 번역만 수행하고 어떠한 수치도 변경하지 않았다. 본문 전체 한글화는 별도 작업.*
