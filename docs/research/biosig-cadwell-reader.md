> Research note produced 2026-09-15 by an LLM research agent (Claude Code, session `adede7d2-9fc1-585c-a838-bea822978308`, see `llm-logs/`) from public sources reachable at the time. Claims are tagged as verified from primary sources or as search-engine snippets/inference where the source could not be opened. Treat as a starting point, not as ground truth; the transcript records exactly what was fetched.

# BioSig (libbiosig) Cadwell support and licensing — research report

Date: 2026-09-15. Sources verified by download unless marked otherwise.

## Access notes (what could and could not be reached)

- `git.ista.ac.at` is blocked by the egress proxy for both WebFetch and curl. Same for `sources.debian.org`, `tracker.debian.org`, `metadata.ftp-master.debian.org`, `salsa.debian.org`, `pub.ista.ac.at`, `mathworks.com`, `researchgate.net`, `wiki.besa.de`, `web.archive.org`.
- Reachable and used instead:
  - SourceForge canonical git (raw file export): `https://sourceforge.net/p/biosig/code/ci/<ref>/tree/<path>?format=raw` — fetched at tag `libbiosig-2.4.2` and at `master`.
  - GitHub mirror `EEGKit/BioSig-sf` ("Unofficial clone of http://biosig.sourceforge.net/ - 20220627"), via raw.githubusercontent.com.
  - PyPI (`Biosig` 3.9.7.post2 sdist), Ubuntu `changelogs.ubuntu.com` copy of `debian/copyright`, SourceForge ticket tracker and commit pages.
- The tag `libbiosig-2.4.2` on SourceForge points to commit `c9ab7bc8c044a44386e563f1a54bddcc106dcc0c`, 2022-06-18, "prepare for release 2.4.2" (`configure.ac`: `AC_INIT([biosig], [2.4.2])`). I could not verify that the git.ista.ac.at tag of the same name points to the same commit, but the SourceForge repo is the URL listed as "Repository" in the PyPI metadata (`https://git.code.sf.net/p/biosig/code`), so it is canonical.
- **The two Cadwell-related files are byte-identical across all three copies** (mirror, SF tag 2.4.2, SF master as of today): `sopen_cadwell_read.c` md5 `51aa1289a889492e539c856daa0c2793` (12 527 bytes); `sopen_sqlite.c` md5 `080e02b2d3db373a90b43fba7a3ce4e7` (7 853 bytes). So what is quoted below is exactly what is in libbiosig 2.4.2 and still in master (libbiosig 3.9.7, July 2026).

All downloaded files are kept under `(session scratchpad, not kept)/biosig/` (`sf242/` = tag 2.4.2, `sfmaster/` = master, `pypi/` = sdist, `ubuntu-copyright`).

---

## 1. What biosig4c++/t210 contains for Cadwell, and what it actually does

### 1.1 Files

Directory listing of `biosig4c++/t210/` at tag `libbiosig-2.4.2` (SourceForge): `LICENSE, abfheadr.h, axon_structs.h, codes.h, scp-decode.cpp, sopen_abf_read.c, sopen_alpha_read.c, sopen_axg_read.c, sopen_cadwell_read.c, sopen_cfs_read.c, sopen_dcmtk_read.cpp, sopen_famos_read.c, sopen_hdf5.c, sopen_heka_read.c, sopen_igor.c, sopen_matio.c, sopen_rhd2000_read.c, sopen_scp_read.c, sopen_sqlite.c, sopen_tdms_read.c, structures.h`.

Two files are Cadwell-related:

| File | Handles | Git history (SourceForge) |
|---|---|---|
| `biosig4c++/t210/sopen_cadwell_read.c` | binary formats `EAS`, `EZ3`, `ARC` (enum values) | added `b6b76d8d…` 2021-07-31 "[b4c] add missing file"; last touched `5d2d8055…` 2021-08-23 "push some work-in-progress: … add some support (for reverse engineering) of EZ3(Cadwell) format …". No commits since. |
| `biosig4c++/t210/sopen_sqlite.c` | SQLite files, intended for Cadwell `.ezdata` ("ARC") | `d99f28e5…` 2021-09-01 "setup sopen_sqlite, sopen_matio, sopen_hdf5 in separate files"; `153fff63…` 2021-09-28 "[b4c] sqlite3: tools to extract column names, number of rows and values of ARC/ezdata/Cadwell data files". No commits since. |

The SourceForge ticket refers to `sopen_cadwell.c`; the actual filename is `sopen_cadwell_read.c`.

### 1.2 Format detection (biosig4c++/biosig.c, tag 2.4.2)

Detection is by magic bytes only; there is **no extension-based detection** for `.eas`/`.ez3`/`.arc`/`.ezdata` (grep for those strings in biosig.c returns nothing).

```c
	else if (!memcmp(Header1, "SctHdr\0\0Directory\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\xff\xff\xff\xff\xff\xff\xff\xff\0\0\0\0\0\0\0\0", 48)
	      && (leu32p((hdr->AS.Header+0x3C))==0x68) ) {
		hdr->TYPE = EAS;
	}
	else if (!memcmp(Header1,"Easy3File",10)) {
		hdr->TYPE = EZ3;
	}
```
(biosig.c lines 1711-1717 at tag 2.4.2)

```c
	else if ((hdr->HeadLen>23) && !memcmp(Header1,"SQLite format 3\000",16) && Header1[21]==64 && Header1[22]==32 && Header1[23]==32 )
		hdr->TYPE = SQLite;
```
(biosig.c line 2014) — i.e. any SQLite 3 file with page-header bytes 21..23 = 64,32,32 (the standard values) is typed `SQLite`.

**`ARC` is never assigned anywhere in biosig.c** — the only occurrences of `ARC` are the enum (`biosig-dev.h` line 229: `EAS, EZ3, ARC,`), the name table (`{ ARC, "ARC(Cadwell)" }`, line 2137) and the dispatch condition. So the "ARC" binary branch in `sopen_cadwell_read` is unreachable dead code; `.ezdata` files go through the `SQLite` branch.

Name table entries: `{ ARC, "ARC(Cadwell)" }`, `{ EAS, "EAS(Cadwell)" }`, `{ EZ3, "EZ3(Cadwell)" }`, `{ SQLite, "SQLite" }`.

### 1.3 Dispatch (biosig.c)

```c
	else if ((hdr->TYPE==EAS) || (hdr->TYPE==EZ3) || (hdr->TYPE==ARC)) {
		while (!ifeof(hdr)) {
			size_t bufsiz = max(2*count, PAGESIZE);
			hdr->AS.Header = (uint8_t*)realloc(hdr->AS.Header, bufsiz+1);
			count  += ifread(hdr->AS.Header+count, 1, bufsiz-count, hdr);
		}
		hdr->AS.Header[count]=0;
		hdr->HeadLen = count;
		ifclose(hdr);

		sopen_cadwell_read(hdr);
	}
```
(lines 6697-6708) — the whole file is slurped into memory, then `sopen_cadwell_read()` is called.

```c
	else if (hdr->TYPE==SQLite) {
		if (VERBOSE_LEVEL>7) fprintf(stdout,"%s (line %d): %s(...)\n", __FILE__,__LINE__,__func__);
		if (sopen_sqlite(hdr)) return(hdr);
	}
```
(lines 10842-10845)

### 1.4 `sopen_cadwell_read.c` — full content summary with key fragments

License header (verbatim, lines 1-21):
```
    Copyright (C) 2021 Alois Schloegl <alois.schloegl@gmail.com>

    This file is part of the "BioSig for C/C++" repository
    (biosig4c++) at http://biosig.sf.net/

    BioSig is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 3
    of the License, or (at your option) any later version.
```

Single function `void sopen_cadwell_read(HDRTYPE* hdr)`, with three branches. **Every branch ends in `biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, ...)`** — the reader never returns a usable header or any samples. It is purely a reverse-engineering scaffold that dumps bytes to files in the current directory (`tmp.bin`, `tmp.asc`, `cadwell.debug.<blockname>`, `cadwell.debug.eeg.txt`). No struct/typedef is defined; all access is via `leu32p/leu64p/lei16p/bei16p` at hard-coded offsets. No decompression. No channel labels, no scaling, no event parsing.

**EAS branch** (Cadwell "Easy" v1/2 `.eas`):
```c
	if (hdr->TYPE==EAS) {
		/* 12 bit ADC ?
		   200 Hz
		   77*800 samples
		   EEGData section has a periodicity of 202*2 (404 bytes)
			800samples*16channels*2byte=25600  = 0x6400)
		*/
		hdr->NS  = 16;  // so far all example files had 16 channels
		hdr->SPR  = 1;
		hdr->NRec = 0;
		hdr->SampleRate = 250;
		unsigned lengthHeader0 = leu32p(hdr->AS.Header + 0x30);
		unsigned lengthHeader1 = leu32p(hdr->AS.Header + 0x34);	// this is varying amoung data sets - meaning unknown
		assert(lengthHeader0==0x0400);

		for (int k=0; k*0x20 < lengthHeader1; k++) {
			char *sectName =       hdr->AS.Header + 0x6c + k*0x20;
			size_t sectPos= leu32p(hdr->AS.Header + 0x7c + k*0x20);
			size_t sectN1 = leu32p(hdr->AS.Header + 0x80 + k*0x20);
			size_t sectN2 = leu32p(hdr->AS.Header + 0x84 + k*0x20);
			size_t sectN3 = leu32p(hdr->AS.Header + 0x88 + k*0x20);

			if (!sectPos
			 || memcmp("SctHdr\0\0", hdr->AS.Header+sectPos, 8)
			 || memcmp(hdr->AS.Header+sectPos+8, sectName, 16))
			{ ... break; }

			uint64_t curSec, nextSec;
			int flag=1;
			do {
				curSec  = leu64p(hdr->AS.Header + sectPos + 24);
				nextSec = leu64p(hdr->AS.Header + sectPos + 32);
				if (flag && !strcmp(sectName,"EEGData")) {
					FILE *fid2=fopen("tmp.bin","w");
					fwrite(hdr->AS.Header + curSec+120, 1, nextSec-curSec-120,fid2);
					fclose(fid2);
					FILE *fid=fopen("tmp.asc","w");
					for (size_t k0=curSec+8*15; k0 < nextSec; k0+=2) {
						fprintf(fid,"%d\n",bei16p(hdr->AS.Header + curSec + k0+1));
					}
					fclose(fid);
					flag = 0;
				}
				sectPos = nextSec;
			} while (nextSec != (size_t)-1L);
		}
		biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, "Format EAS(Cadwell): unsupported ");
	}
```
What this tells us about `.eas`: file starts with `"SctHdr\0\0Directory"` (48-byte magic, see 1.2) and `u32 @0x3C == 0x68`; `u32 @0x30 == 0x400` (header length); a directory of 0x20-byte section entries starting at 0x6C: 16-byte name, `u32 pos @+0x10`, three more u32 at +0x14/+0x18/+0x1C; each section begins with `"SctHdr\0\0"` + 16-byte name, `u64 @+24` = current segment offset, `u64 @+32` = next segment offset (chain terminated by `0xFFFFFFFFFFFFFFFF`); a section named `"EEGData"`. The author's comments contradict each other on sample rate (comment says 200 Hz, code sets 250) and ADC width ("12 bit ADC ?"); "so far all example files had 16 channels". Note the data dump reads **big-endian** int16 at an odd offset (`bei16p(... + k0+1)`) — clearly experimental probing, not a decoder.

**EZ3 branch** (Cadwell "Easy III" `.ez3`):
```c
	else if (hdr->TYPE==EZ3) {
		hdr->VERSION = strtod((char*)hdr->AS.Header+21, NULL);
		// 16 bit ADC ?
		// 250 Hz ?
		uint32_t posH1  = leu32p(hdr->AS.Header + 0x10);
		uint32_t posH1b = leu32p(hdr->AS.Header + 0x20);
		uint32_t posH2  = leu32p(hdr->AS.Header + 0x38);
		uint32_t posH2b = leu32p(hdr->AS.Header + posH1 + 0x38);
		assert(posH1==posH1b);
		assert(posH2==posH2b);

		// start date/time
		{
			char *tmp = hdr->AS.Header + 0x5c;
			struct tm t;
			t.tm_year = strtol(tmp,&tmp,10)-1900;
			t.tm_mon = strtol(tmp+1,&tmp,10)-1;
			t.tm_mday = strtol(tmp+1,&tmp,10);
			t.tm_hour = strtol(tmp+1,&tmp,10);
			t.tm_min = strtol(tmp+1,&tmp,10);
			t.tm_sec = strtol(tmp+1,&tmp,10);
			hdr->T0 = tm_time2gdf_time(&t);
		}

		uint32_t pos0 = posH1+0x40;
		for (size_t k = posH1+0x40; k < posH2; k += 0x30) {
			char *tmp    = hdr->AS.Header + k + 1;          // block label (e.g. "EEG001", "EVENT001")
			uint32_t pos = leu32p(hdr->AS.Header + k + 0x28); // block position
			if (tmp[0]=='\0') break;
			if (pos<pos0) break;

			uint32_t V16=leu32p(hdr->AS.Header+pos+16);	// related to size current block, seems to match next pos-pos0-64, V16+pos+64 is next pos.
			uint32_t V20=leu32p(hdr->AS.Header+pos+20);	// always(?) 0
			uint32_t V24=leu32p(hdr->AS.Header+pos+24);	// related to block type, or position, seems to be a decimal number, 0,1,27000,151000,329000
			uint32_t V32=leu32p(hdr->AS.Header+pos+32);	// import for EEG001 blocks ?
			char*    next    =  hdr->AS.Header+pos+40;	// string, refers to name of next block ??
			uint32_t nextpos =  leu32p(hdr->AS.Header + k + 0x28 + 0x30);
			uint32_t V64..V80, V236,V237,V244,V245,V260,V261,V324,V332 ...  // all "seems to be important ... ?"

			... fopen("cadwell.debug.<next>","a") ...

			if (VERBOSE_LEVEL > 7) {
				if (memcmp(hdr->AS.Header+pos,"EasyDCWYAAA\0@\0\0\0",16) || leu32p(hdr->AS.Header+pos+20) )
					fprintf(stdout,"... unexpected header info ...");
				if (nextpos != V16+pos+64) fprintf(stdout,"... unexpected header info %d!=%d\n", nextpos, V16+pos+64);
				...
			}

			if (!strncmp(next, "EEG001",7)) {
				/* positions with differences in the range of [0..371]
					    16    17    24    25    32   237   238   245   261   262   324   325   332 */
				if (V76 != 0x2addcb81L) ...
				if (V80 != 0x02) ...
				if (V32 != 1000) ...
				if (V237 != V24) ...
				if (V245 != 1000) ...
				if (V261 != V24) ...
				if (V324 != V24) ...
				if (V332 != 250)	// sampling rate, SPR ?
				if (V332*4 != V32 || V32 != V245) ...
/*
				start at 372-872: block1
				block2 615-1114:
				block2 1433-
				next interval seem seem to have variable lengths
				(signed) int16
				blocklengths 308 samples, 250 real samples + ?
*/
				strcpy(TMP, "cadwell.debug.eeg.txt");
				FILE* fid = fopen(TMP,"a");
				for (size_t kk=0; kk<V332; kk++) {
					int16_t v1=lei16p(hdr->AS.Header+pos+371+kk*2);
					int16_t v2=lei16p(hdr->AS.Header+pos+371+(V332*2+63*2)+kk*2);
					int16_t v3=lei16p(hdr->AS.Header+pos+371+(V332*2+63*2)*2+kk*2);
					fprintf(fid, "%d\t%d\t%d\n", v1,v2,v3);
				}
				fclose(fid);
			}
			else if (!strncmp(next,"EVENT001",9)) {
				/* positions with differences in the range of [0..2051]
				   18    537 ... 552   1217   1402
				   after 2052, almost all bytes a diffent */
				if (V76 != 0) ...
				if (V80 != 0x20c00) ...
				if (hdr->AS.Header[pos+165]!='E' || hdr->AS.Header[pos+202]!='t' ) ...
			}
			else { if (V76 != 0) ... if (V80 != 0x20c00) ... }
		}
		biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, "Format EZ3(Cadwell): unsupported ");
	}
	else if (hdr->TYPE==ARC) {
		biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, "Format ARC(Cadwell): unsupported ");
	}
```
What this tells us about `.ez3`: magic `"Easy3File"` (10 bytes incl. NUL); version as ASCII float at offset 21; `u32 @0x10 == u32 @0x20` = position of a header-1 block; `u32 @0x38` = position of header-2 block (also stored at `posH1+0x38`); start date/time as ASCII `YYYY-MM-DD HH:MM:SS`-like at 0x5C; a directory of 0x30-byte entries beginning at `posH1+0x40`: label at +1 (NUL-terminated), `u32 @+0x28` = block position; each data block starts with 16-byte magic `"EasyDCWYAAA\0@\0\0\0"`, `u32 @+16` = block size (next = pos+V16+64), `@+40` = name of block ("EEG001", "EVENT001", ...); in EEG001 blocks int16 LE samples appear to start at +371 (odd offset, again suspicious) in sub-blocks of `V332(=250)+63` samples; V332 (=250) guessed as sampling rate. Everything is annotated with `?` — it's guesswork the author explicitly labelled "for reverse engineering".

Completeness markers: the function contains 20+ comments ending in `?`, "meaning unknown", "so far all example files", "seems to be", an `#if 0` block, `assert()`s, hard-coded debug file dumps, and three `biosigERROR(... "unsupported ")` terminators. There is no `TODO` keyword in this file, but the SQLite file has one (below). No struct layouts are defined.

### 1.5 `sopen_sqlite.c` — the `.ezdata` (SQLite) path

Same GPL-3-or-later header, Copyright (C) 2021 Alois Schloegl. Links sqlite3 only when compiled with `WITH_SQLITE3`:
```c
#ifdef WITH_SQLITE3
#include <sqlite3.h>
#endif
```
Build system (`biosig4c++/Makefile.in` at tag 2.4.2, lines 277-279):
```make
ifeq (1,@HAVE_SQLITE3@)
	DEFINES    += -DWITH_SQLITE3=1 -DSQLITE_THREADSAFE=0 -DSQLITE_OMIT_LOAD_EXTENSION
	LDLIBS     += -lsqlite3
```
but in the top-level `configure.ac` (line 27) the check is **commented out**:
```
# AC_CHECK_LIB([sqlite3], [sqlite3_open],        AC_SUBST(HAVE_SQLITE3,    "1") )
```
So a default build of libbiosig 2.4.2 does **not** link sqlite3, and `sopen_sqlite()` then returns:
`"SOPEN(SQLite): - sqlite format not supported - libbiosig need to be recompiled with libsqlite3 support."`

When compiled with sqlite3, the function identifies a Cadwell file by the presence of 11 tables:
```c
	/*
		Identify whether it is an Cadwell EZDATA file or not
		Cadwell has these tables:
	*/
	strcpy(zSql, "SELECT COUNT(*) AS x FROM FrameInfo;"
	"SELECT COUNT(*) AS a FROM MiscInfo;"
	"SELECT COUNT(*) AS b FROM TrackInfoSyncRowData;"
	"SELECT COUNT(*) AS c FROM MaxUpdateTick;"
	"SELECT COUNT(*) AS d FROM MiscInfoSyncRowData;"
	"SELECT COUNT(*) AS e FROM syncrowdata;"
	"SELECT COUNT(*) AS f FROM MediaHeader;"
	"SELECT COUNT(*) AS g FROM SchemaUpdateLog;"
	"SELECT COUNT(*) AS h FROM synctable;"
	"SELECT COUNT(*) AS i FROM MediaHeaderSyncRowData;"
	"SELECT COUNT(*) AS j FROM TrackInfo;");
	...
	const char *ARC_TableList[]={"FrameInfo", "MiscInfo", "TrackInfoSyncRowData", "MaxUpdateTick", "MiscInfoSyncRowData", "syncrowdata", "MediaHeader", "SchemaUpdateLog", "synctable", "MediaHeaderSyncRowData", "TrackInfo", NULL};
```
It then does `SELECT * FROM <table>` for each, prints column names (`sqlite3_column_origin_name`) and the first 10 rows (hex-dumping BLOBs at verbose level > 8), closes the DB, and ends with:
```c
	/* TODO:
		- check whether it is a recognized and supported data set (i.e. Cadwell/ARC format)
		- fill in HDRstruct* hdr
		- extract data samples and fill hdr->data
		- fill event table if applicable
		Once these steps are completed, the following line can be removed
	 */
	biosigERROR(hdr, B4C_FORMAT_UNSUPPORTED, "Format SQLite: not supported yet.");
```
Nothing is decoded: no column names, no BLOB layout, no channel/sample-rate extraction. Note also `int sopen_sqlite(HDRTYPE*)` contains bare `return;` (no value) and a stray `otherwise:` label — it is unpolished, likely never compiled in release builds.

### 1.6 Bottom line on completeness

- Detected but **unsupported**: `.eas` (EAS), `.ez3` (EZ3), `.ezdata` (SQLite). All three code paths deliberately fail with `B4C_FORMAT_UNSUPPORTED`. "ARC" as a binary type is never detected.
- Nothing has changed in these files since 2021-08-23 / 2021-09-28; they are identical in libbiosig 2.4.2 (2022-06) and master (3.9.7, 2026-07). Upstream RELEASE-NOTES (master) do not mention Cadwell in any version or in the "Work-in-progress / planned" list.
- The only reusable knowledge is: the magic byte strings, the section-directory layout of EAS, the block-directory layout of EZ3 (with big uncertainty), and the list of 11 table names in `.ezdata`. None of it constitutes a working decoder; a port would still require reverse engineering the sample encoding.

---

## 2. License of libbiosig / biosig4c++

- Top-level `COPYING` (SourceForge master, 35 147 bytes): `GNU GENERAL PUBLIC LICENSE / Version 3, 29 June 2007`. There is no separate `COPYING`/`LICENSE` inside `biosig4c++/` (verified: 404 at tag and master; directory listing shows none).
- `biosig4c++/t210/LICENSE` (18 009 bytes) is the text of **GPL Version 2, June 1991**. Its git history: added 2006-02-13 "reading SCP data: Eugenio's initial code" — it is a leftover from the imported SCP decoder, not a statement of the library's license.
- Per-file headers of both Cadwell files: **"GNU General Public License … either version 3 of the License, or (at your option) any later version"** → **GPL-3.0-or-later** (verbatim quoted in 1.4).
- Debian/Ubuntu `debian/copyright` (fetched from `https://changelogs.ubuntu.com/changelogs/pool/universe/b/biosig/biosig_2.5.2-1build1/copyright`): `Files: * … License: GPL-3+`; exceptions only for `biosig4c++/XMLParser/tiny*` (ZLIB) and the asn1c-generated `biosig4c++/t240/*` (BSD-4-clause). The Cadwell files fall under `Files: *` → GPL-3+.
- PyPI `Biosig` 3.9.7.post2: `License-Expression: GPL-3.0-only`, bundled `LICENSE` = GPL v3 text. (Slight inconsistency with the file headers' "or later"; the source headers govern for the C code.)
- `biosig4c++/README` line 174: "Copyright (C) 2005-2020 Alois Schloegl", no license sentence.

Conclusion: **libbiosig / biosig4c++ (including sopen_cadwell_read.c and sopen_sqlite.c) is GPL-3.0-or-later**; distributions and PyPI label it GPL-3(+).

---

## 3. Documentation / changelog / tickets about Cadwell support

- SourceForge feature request #13, "Support for AES, EZ3, and ARC fiile formats", opened 2021-08-27 by Alois Schloegl, status Open, owner nobody: "AES, EZ3 and ARC are proprietary EEG data formats. EEG data is stored in this format by products of Cadwell. Unfortunately, Cadwell does not provide the specification…". Comment 2021-09-30: "The files biosig4c++/t210/sopen_cadwell.c and biosig4c++/t210/sopen_sqlite.c are used to develop tools for reverse engineering, and understanding and implementing support for these data formats. The extracted information can be shown with `save2gdf -V9 <filename>`" (verbosity 8 or 9). URL: https://sourceforge.net/p/biosig/feature-requests/13/ ("AES" there is a typo for EAS.)
- Commits (all by Alois Schloegl, SourceForge):
  - `b6b76d8d25a3e14192e3822835f9f4c4df200994` 2021-07-31 "add missing file" (adds sopen_cadwell_read.c)
  - `5d2d8055f5fafa9dfc82b61aef3de8eb68991291` 2021-08-23 "push some work-in-progress: - add some support for GTF - add some support (for reverse engineering) of EZ3(Cadwell) format; …" (touches biosig.c, sopen_cadwell_read.c, CMakeLists.txt, …)
  - `d99f28e5eec5b23a07e3a474d4c8015c621207fc` 2021-09-01 "setup sopen_sqlite, sopen_matio, sopen_hdf5 in separate files"
  - `153fff632caa6b92702644f79b2adffc6153f667` 2021-09-28 "[b4c] sqlite3: tools to extract column names, number of rows and values of ARC/ezdata/Cadwell data files"
- RELEASE-NOTES (master, up to 3.9.7 of 2026-07-17): no Cadwell/EZ3/EAS/ARC entry at all. NEWS (both SourceForge web NEWS and biosig4c++/NEWS): none. Legacy CHANGELOG (stopped 2013) has an unrelated "add SQLite identification" line.
- The list of supported formats (`http://pub.ist.ac.at/~schloegl/biosig/TESTED`) could not be fetched (host blocked); given the code, Cadwell cannot be listed as supported there.
- No mailing-list posts found by web search.

---

## 4. Python binding and other open-source Cadwell readers

**pip `Biosig`** (https://pypi.org/project/Biosig/): 3.9.7.post2, 2026-07-26; GPL-3.0-only. The sdist contains only `biosigmodule.c/.h`, `setup.py`, `README.md`, `LICENSE`, `demo2.py` — it does **not** bundle libbiosig; it links a system `libbiosig` (`apt install libbiosig-dev`, `brew install biosig`, Windows wheels bundle a prebuilt DLL). Exposed functions: `biosig.header()`, `biosig.jsonheader()`, `biosig.tomlheader()`, `biosig.data()`. It is a thin wrapper over `sopen/sread`, so whatever libbiosig detects is "exposed" — but for Cadwell files it would just raise the `B4C_FORMAT_UNSUPPORTED` error. No Cadwell mention anywhere in the package. Debian/Ubuntu: source package `biosig` 2.5.2 builds `libbiosig3, libbiosig-dev, biosig-tools, python3-biosig, octave-biosig` (Launchpad).

**Other open-source readers — none found that actually decode Cadwell data:**
- MNE-Python: no Cadwell reader in the I/O tutorial; GitHub issue search `cadwell repo:mne-tools/mne-python` → 0 results.
- python-neo: 0 issues mentioning Cadwell; not in format list.
- pyedflib / EDFbrowser: EDF-only; no Cadwell import.
- GitHub code search: the only hits for `sopen_cadwell`, `EasyDCWYAAA`, `TrackInfoSyncRowData` are the BioSig mirror itself. `search_repositories "cadwell eeg"` → 0 repos. `Pennsieve/persyst-deidentify` maps `"arc": "Cadwell", "ez3": "Cadwell"` but only as a driver for the commercial Persyst `PSCLI.exe`.
- PyPI: no `cadwell`, `pycadwell`, `cadwell-eeg` packages; `ezdata` on PyPI and `vtciald/ezdata` on GitHub are unrelated (dataclass helper / survey-data lib).
- Community knowledge (from search snippets of MATLAB Answers #480265, page itself blocked; not independently verified): `.ezdata` is "SQLite format 3"; EEG samples are in table `FrameInfo` with columns `DataKey`, `FrameKey`, `Data` (BLOB); one test file had 1199 rows for a 1199-s recording at ~500 Hz, ~20 channels (i.e. one row per second). BLOB layout not documented publicly.
- Commercial readers that do handle Cadwell: Persyst, BESA (BESA's reader "requires the installation of the Cadwell Arc API", per search snippet of wiki.besa.de — page blocked), and Cadwell's own Arc software/API (Arc EEG 3.1 "next-gen API … for researchers and development partners"). Cadwell does not publish the format.

---

## 5. Licensing analysis for CwellEEGRead (currently Unlicense)

**Option A — port/derive from `sopen_cadwell_read.c` / `sopen_sqlite.c`.** This code is GPL-3.0-or-later. Any translation (C→Python etc.) or adaptation is a derivative work; it cannot be released under the Unlicense/public domain. The repo would have to be relicensed to GPL-3.0-or-later (or a GPL-3-compatible outbound license that is effectively GPL for the combined work, e.g. keeping the ported file GPL-3.0-or-later and the whole distribution under GPL-3.0-or-later). Practically: change `LICENSE`, add SPDX headers, keep the copyright notice "Copyright (C) 2021 Alois Schloegl" and attribution. Strong recommendation: **not worth it** — the code contains no working decoder, only magic strings and offset guesses; the GPL cost buys almost nothing.

**Option B — clean-room reimplementation from format knowledge (recommended).** Facts are not copyrightable: magic byte values (`"SctHdr\0\0Directory…"`, `"Easy3File"`, `"EasyDCWYAAA\0@\0\0\0"`), file offsets, table names (`FrameInfo`, `TrackInfo`, `MediaHeader`, …) and column names are format facts, not expression. Writing your own parser from your own analysis of sample files (plus these facts) keeps the Unlicense intact. To keep it defensible: do not copy BioSig's code structure, variable names (`posH1`, `V332`…) or comments; cite the BioSig files only as prior reverse-engineering notes (and the SF ticket) in a NOTES/README. Given that `.ezdata` is a SQLite DB, Python's stdlib `sqlite3` plus your own BLOB decoding is the natural path and needs no BioSig code at all.

**Option C — link libbiosig as a dependency.** Linking (statically or via ctypes/`pip install biosig`) to a GPL library makes the combined program GPL when distributed; the Unlicense repo could stay Unlicense only for its own files if you accept that the distributed whole is under GPL terms, which is awkward and, more importantly, pointless: **libbiosig cannot read any Cadwell format** (every path returns `B4C_FORMAT_UNSUPPORTED`, and the SQLite path is not even compiled in by default because the `AC_CHECK_LIB([sqlite3]…)` line is commented out in configure.ac). So there is nothing to gain from a dependency.

**Recommendation:** Option B. Treat BioSig as a source of a few verified facts (magic strings, table list, the EAS section-directory layout), acknowledge it in documentation, and write an independent implementation. If the project ever wants to reuse actual BioSig code, switch the repository license to GPL-3.0-or-later before merging it.

---

## Key URLs

- Canonical git (reachable): https://sourceforge.net/p/biosig/code/ci/libbiosig-2.4.2/tree/biosig4c++/t210/sopen_cadwell_read.c (append `?format=raw`), …/sopen_sqlite.c
- Tag commit: https://sourceforge.net/p/biosig/code/ci/libbiosig-2.4.2/ (c9ab7bc8, 2022-06-18)
- File history: https://sourceforge.net/p/biosig/code/ci/master/log/?path=/biosig4c%2B%2B/t210/sopen_cadwell_read.c ; …/sopen_sqlite.c
- GitHub mirror (2022-06-27 snapshot): https://github.com/EEGKit/BioSig-sf/blob/master/biosig4c++/t210/sopen_cadwell_read.c
- Feature request: https://sourceforge.net/p/biosig/feature-requests/13/
- Ubuntu copyright file: https://changelogs.ubuntu.com/changelogs/pool/universe/b/biosig/biosig_2.5.2-1build1/copyright
- PyPI: https://pypi.org/project/Biosig/ ; Launchpad: https://launchpad.net/ubuntu/+source/biosig/2.5.2-1build1
- Upstream GitLab (blocked here, unverified): https://git.ista.ac.at/alois.schloegl/biosig/-/tree/libbiosig-2.4.2/biosig4c++/t210
- MATLAB Answers thread on .ezdata (blocked here; content from search snippets only): https://www.mathworks.com/matlabcentral/answers/480265-reading-clinical-eeg-ezdata-file-in-matlab
