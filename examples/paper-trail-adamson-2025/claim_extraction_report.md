# Claim extraction validation — `paper-trail-adamson-2025`

**88 claims total · 78 PASS · 10 FLAG**

## Flag breakdown

- `TEXT_ANCHOR_MISSING`: **6**
- `CITEKEY_MARKER_MISMATCH`: **4**

## Flagged claims

### C012 · `wang2003` (ref 11)

> such as Multiscale SSIM (MSSIM11) and FSIM12

- **TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)**

### C027 · `zhao2022` (ref 26)

> zhao2022 is a fastMRI dataset extension/companion paper providing pathology annotations for the fastMRI corpus.

- **TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)**

### C036 · `deng2009` (ref 35)

> The manuscript paragraph context says "ImageNet[36] / pre-training" — sub-claim for ref 36 (deng2009): deng2009 is the original ImageNet pap…

- **TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)**

### C040 · `huang2023` (ref 39)

> [v1 placeholder] huang2023 is cited in support of supervised/ImageNet pretraining providing good features for deep-feature-distance (DFD) / …

- **TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)**

### C054 · `zhouwang2004` (ref 45)

> zhouwang2004 specifies the standard SSIM hyperparameters (Gaussian window, K1=0.01, K2=0.03, dynamic range L=255) used in the manuscript's N…

- **CITEKEY_MARKER_MISMATCH — claim cites zhouwang2004 (ref 45), but nearby markers are [7, 8, 9, 5, 6]**
- Matched window `nrmse ssim psnr` at offset 4236
- Nearby markers: [7, 8, 9, 5, 6]

### C058 · `ding2020` (ref 28)

> DISTS uses the same φ(l)_D as LPIPS, but with a distance function G inspired by the form of SSIM that assesses texture and structure similar…

- **CITEKEY_MARKER_MISMATCH — claim cites ding2020 (ref 28), but nearby markers are [34, 2, 1, 47]**
- Matched window `lpips distance function inspired form` at offset 18074
- Nearby markers: [34, 2, 1, 47]

### C061 · `simonyan2014` (ref 46)

> simonyan2014 introduces the VGG architecture, used as the deep feature extractor in many DFD metrics (LPIPS uses VGG).

- **CITEKEY_MARKER_MISMATCH — claim cites simonyan2014 (ref 46), but nearby markers are [6]**
- Matched window `dfd metrics lpips` at offset 37430
- Nearby markers: [6]

### C064 · `pathak2016` (ref 48)

> pathak2016 cited as a representative self-supervised learning method via inpainting / context-based pretext tasks; used as background for SS…

- **TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)**

### C070 · `desai2021` (ref 51)

> Adamson et al. used this approach to train a DL model for image reconstruction with a feature distance loss measured against an SSFD pre-tra…

- **TEXT_ANCHOR_MISSING — no 3-5 word window of claim_text appears in paper.txt (paraphrase or fabrication)**

### C071 · `mason2020` (ref 6)

> Correlations in terms of SROCC of mean reader scores versus the IQ metric scores for each of the IQMs are reported in Figure 4 (Right).

- **CITEKEY_MARKER_MISMATCH — claim cites mason2020 (ref 6), but nearby markers are [2, 16, 50, 3]**
- Matched window `correlations terms srocc mean reader` at offset 25683
- Nearby markers: [2, 16, 50, 3]

## Passed claims (for reference)

<details><summary>Click to expand</summary>

- C001 · `lustig2007` (ref 1)
- C002 · `sandino2020` (ref 2)
- C003 · `hammernik2021` (ref 3)
- C004 · `hammernik2018` (ref 4)
- C005 · `chen2022` (ref 5)
- C006 · `mason2020` (ref 6)
- C007 · `mason2020` (ref 6)
- C008 · `chaudhari2018` (ref 7)
- C009 · `chaudhari2020` (ref 8)
- C010 · `mardani2019` (ref 9)
- C011 · `zhouwang2011` (ref 10)
- C013 · `linzhang2011` (ref 12)
- C014 · `miao2008` (ref 13)
- C015 · `mantiuk2011` (ref 14)
- C016 · `miao2013` (ref 15)
- C017 · `salem2002` (ref 16)
- C018 · `daly1992` (ref 17)
- C019 · `sheikh2006` (ref 18)
- C020 · `dameravenkata2000` (ref 19)
- C021 · `ravishankar2011` (ref 20)
- C022 · `kim2018` (ref 21)
- C023 · `chan2021` (ref 22)
- C024 · `kleineisel2025` (ref 23)
- C025 · `desai2022` (ref 24)
- C026 · `zhao2021` (ref 25)
- C028 · `zhang2018` (ref 27)
- C029 · `ding2020` (ref 28)
- C030 · `cong2022` (ref 29)
- C031 · `cheon2021` (ref 30)
- C032 · `lao2022` (ref 31)
- C033 · `conde2022` (ref 32)
- C034 · `keshari2022` (ref 33)
- C035 · `gu2022` (ref 34)
- C037 · `raghu2019` (ref 36)
- C038 · `mei2022` (ref 37)
- C039 · `cadrinchenevert2022` (ref 38)
- C041 · `kastryulin2023` (ref 40)
- C042 · `wang2024` (ref 41)
- C043 · `knoll2020` (ref 42)
- C044 · `sandino2020` (ref 2)
- C045 · `knoll2020` (ref 42)
- C046 · `xin2023` (ref 43)
- C047 · `uecker2014` (ref 44)
- C048 · `gu2022` (ref 34)
- C049 · `chen2022` (ref 5)
- C050 · `sheikh2006` (ref 18)
- C051 · `sheikh2006` (ref 18)
- C052 · `dameravenkata2000` (ref 19)
- C053 · `zhouwang2004` (ref 45)
- C055 · `miao2008` (ref 13)
- C056 · `chen2022` (ref 5)
- C057 · `sandino2020` (ref 2)
- C059 · `gu2022` (ref 34)
- C060 · `gu2022` (ref 34)
- C062 · `lustig2007` (ref 1)
- C063 · `adamson2021` (ref 47)
- C065 · `dominic2023` (ref 49)
- C066 · `mei2022` (ref 37)
- C067 · `vandersluijs2023` (ref 50)
- C068 · `vandersluijs2023` (ref 50)
- C069 · `vandersluijs2023` (ref 50)
- C072 · `mason2020` (ref 6)
- C073 · `mei2022` (ref 37)
- C074 · `cadrinchenevert2022` (ref 38)
- C075 · `vandersluijs2023` (ref 50)
- C076 · `vandersluijs2023` (ref 50)
- C077 · `wang2024` (ref 41)
- C078 · `li2020` (ref 52)
- C079 · `jin2019` (ref 53)
- C080 · `mason2020` (ref 6)
- C081 · `mei2022` (ref 37)
- C082 · `cadrinchenevert2022` (ref 38)
- C083 · `kastryulin2023` (ref 40)
- C084 · `dar2019` (ref 54)
- C085 · `mason2020` (ref 6)
- C086 · `wang2024` (ref 41)
- C087 · `luisier2008` (ref 55)
- C088 · `desai2023` (ref 56)

</details>
