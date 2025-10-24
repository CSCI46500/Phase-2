# metrics.py
from __future__ import annotations
import time
from typing import Dict
from model import Model
from collections import OrderedDict

class Metrics:
    def __init__(self, inputs: Dict[str, str]) -> None:
        self.mod = Model(
            code_url = inputs.get("code_url", ""),
            dataset_url= inputs.get("dataset_url", ""),
            model_url= inputs.get("model_url", "")
        )

    def _ms(self, seconds: float) -> int:
        return int(round(seconds * 1000.0))

    # Runs all metrics computations
    def run(self) -> Dict[str, float]:
        license_res = self.compute_license()
        size_res = self.compute_size()
        ramp_res = self.compute_ramp_up()
        bus_res = self.compute_bus_factor()
        perf_res = self.compute_perf_claims()
        ds_code_res = self.compute_ds_code()
        ds_quality_res = self.compute_ds_quality()
        code_quality_res = self.compute_code_quality()

        temp_scores = {}
        temp_scores.update(license_res)
        temp_scores.update(size_res)
        temp_scores.update(ramp_res)
        temp_scores.update(bus_res)
        temp_scores.update(perf_res)
        temp_scores.update(ds_code_res)
        temp_scores.update(ds_quality_res)
        temp_scores.update(code_quality_res)
        net_res = self.compute_net(temp_scores)

        format_results = OrderedDict([
            ("name", self.mod.model_dict.get("name")),
            ("category", "MODEL"),
            ("net_score", net_res["net_score"]),
            ("net_score_latency", net_res["net_score_latency"]),
            ("ramp_up_time", ramp_res["ramp_up_time"]),
            ("ramp_up_time_latency", ramp_res["ramp_up_time_latency"]),
            ("bus_factor", bus_res["bus_factor"]),
            ("bus_factor_latency", bus_res["bus_factor_latency"]),
            ("performance_claims", perf_res["performance_claims"]),
            ("performance_claims_latency", perf_res["performance_claims_latency"]),
            ("license", license_res["license"]),
            ("license_latency", license_res["license_latency"]),
            ("size_score", size_res["size_score"]),
            ("size_score_latency", size_res["size_score_latency"]),
            ("dataset_and_code_score", ds_code_res["dataset_and_code_score"]),
            ("dataset_and_code_score_latency", ds_code_res["dataset_and_code_score_latency"]),
            ("dataset_quality", ds_quality_res["dataset_quality"]),
            ("dataset_quality_latency", ds_quality_res["dataset_quality_latency"]),
            ("code_quality", code_quality_res["code_quality"]),
            ("code_quality_latency", code_quality_res["code_quality_latency"]),
            ]
        )

        return format_results

    def compute_license(self) -> Dict[str, float]:
        # License compatible with LGPLv2.1
        LGPLV21_COMPATIBLE_LICENSES = {
            "mit",
            "apache",
            "lgpl-2.1",
            "bsd-3-clause",
            "bsd-2-clause",
            "mpl"
        }

        t0 = time.time()
        license_str = self.mod.get_license().lower()
        license_score = 1.0 if any(l in license_str for l in LGPLV21_COMPATIBLE_LICENSES) else 0.0
        license_latency = self._ms(time.time() - t0)

        return {
            "license": license_score,
            "license_latency": license_latency
        }

    def compute_size(self) -> Dict[str, float]:
        SIZE_THRESHOLDS_GB: Dict[str, float] = {
            "raspberry_pi": 0.5,
            "jetson_nano": 1.0,
            "desktop_pc": 6.0,
            "aws_server": 15.0,
        }

        t0 = time.time()
        size_gb = self.mod.get_size()
        size_score = {
            dev: round(min(max(0.0, 1.0 - size_gb / limit), 1.0), 2) if size_gb > 0 else 0.0
            for dev, limit in SIZE_THRESHOLDS_GB.items()
        }

        size_latency = self._ms(time.time() - t0)
        
        return {
            "size_score": size_score,
            "size_score_latency": size_latency
        }

    def compute_ramp_up(self) -> Dict[str, float]:
        RAMP_UP_SECTIONS = [
            "install",
            "installation",
            "usage",
            "example",
            "quickstart",
            "quick start",
            "download",
            "how to use"
        ]
        
        MIN_WORDS_THRESHOLD = 50
        t0 = time.time()
        readme_text = self.mod.fetch_readme("code").lower()
        section_scores = []

        for section in RAMP_UP_SECTIONS:
            if section in readme_text:
                idx = readme_text.index(section) + len(section)
                after_text = readme_text[idx:]
                next_idx = len(after_text)
                for next_section in RAMP_UP_SECTIONS:
                    ni = after_text.find(next_section)
                    if ni != -1 and ni < next_idx:
                        next_idx = ni
                section_content = after_text[:next_idx].split()
                meaningful_words = [w for w in section_content if w not in ("more", "information", "see", "docs")]
                score = min(len(meaningful_words) / MIN_WORDS_THRESHOLD, 1.0)
                section_scores.append(score)
            else:
                section_scores.append(0.0)

        ramp_up_score = round(sum(section_scores) / len(section_scores), 2) if section_scores else 0.0
        ramp_latency = self._ms(time.time() - t0)

        return {
            "ramp_up_time": ramp_up_score,
            "ramp_up_time_latency": ramp_latency
        }
    
    def compute_perf_claims(self) -> Dict[str, float]:
        t0 = time.time()
        PERF_KWS = ["accuracy", "benchmark", "perplexity", "performance"]
        readme_text = self.mod.fetch_readme("code").lower()
        perf_score = 1.0 if any(kw in readme_text for kw in PERF_KWS) else 0.0
        perf_latency = self._ms(time.time() - t0)

        return {
            "performance_claims": perf_score,
            "performance_claims_latency": perf_latency
        }

    def compute_bus_factor(self) -> Dict[str, float]:
        t0 = time.time()
        num_contrib = self.mod.get_contrib()
        if num_contrib >= 10:
            bus_factor_score = 1.0
        elif num_contrib < 10 and num_contrib >= 7:
            bus_factor_score = 0.5
        elif num_contrib < 7 and num_contrib >= 5:
            bus_factor_score = 0.3
        else:
            bus_factor_score = 0.0

        bus_latency = self._ms(time.time() - t0)

        return {
            "bus_factor": bus_factor_score,
            "bus_factor_latency": bus_latency
        }

    def compute_ds_code(self) -> Dict[str, float]:
        t0 = time.time()
        has_code = bool(self.mod.code_dict)
        has_ds = bool(self.mod.dataset_dict)
        ds_code_score = (float(has_code) + float(has_ds)) / 2.0
        ds_code_latency = self._ms(time.time() - t0)

        return {
            "dataset_and_code_score": ds_code_score,
            "dataset_and_code_score_latency": ds_code_latency
        }
    
    def compute_ds_quality(self) -> Dict[str, float]:
        t0 = time.time()
        ds_readme_len = self.mod.len_readme("dataset")
        if ds_readme_len >= 820:
            ds_readme_point = 0.3
        else:
            ds_readme_point = 0.0

        ds_downloads = self.mod.get_downloads()
        if ds_downloads >= 100000:
            ds_download_point = 0.2
        elif ds_downloads < 100000 and ds_downloads >= 50000:
            ds_download_point = 0.15
        else:
            ds_download_point = 0.0

        DATASET_KWS = ["license", "download", "split", "train", "test", "validation"]
        ds_kw_point = 0.5 if self.mod.kw_check(DATASET_KWS, "dataset") else 0.0

        ds_quality_score = ds_readme_point + ds_download_point + ds_kw_point
        ds_quality_latency = self._ms(time.time() - t0)

        return {
            "dataset_quality": ds_quality_score,
            "dataset_quality_latency": ds_quality_latency
        }

    def compute_code_quality(self) -> Dict[str, float]:
        t0 = time.time()
        repo_stats = self.mod.get_git_stats()
        repo_readme_len = self.mod.len_readme("code")
        if repo_stats.get("stars", 0) >= 10000:
            repo_stats_point = 0.1
        else:
            repo_stats_point = 0.0

        if repo_stats.get("forks", 0) >= 5000:
            repo_stats_point += 0.1
        else:
            repo_stats_point += 0.0

        if repo_readme_len >= 1700:
            repo_readme_point = 0.3
        elif repo_readme_len < 1700 and repo_readme_len >= 1000:
            repo_readme_point = 0.2
        else:
            repo_readme_point = 0.0

        maintenance_point = 0.2 if self.mod.last_modified("github", 180) else 0.0
        code_quality_score = repo_stats_point + repo_readme_point + maintenance_point
        code_latency = self._ms(time.time() - t0)

        return {
            "code_quality": code_quality_score,
            "code_quality_latency": code_latency
        }

        
    def compute_net(self, scores: Dict[str, float]) -> Dict[str, float]:
        t0 = time.time()
        weights = {
            "license": 0.2,
            "size": 0.1,
            "ramp": 0.12,
            "bus": 0.12,
            "perf": 0.1,
            "ds_code": 0.1,
            "ds_quality": 0.13,
            "code_quality": 0.13
        }
        license_score = scores["license"]
        size_score = min(scores["size_score"].values())
        ramp_score = scores["ramp_up_time"]
        bus_score = scores["bus_factor"]
        perf_score = scores["performance_claims"]
        ds_code_score = scores["dataset_and_code_score"]
        ds_quality = scores["dataset_quality"]
        code_quality = scores["code_quality"]

        net_score = (
            license_score * weights["license"] +
            size_score * weights["size"] +
            ramp_score * weights["ramp"] +
            bus_score * weights["bus"] +
            perf_score * weights["perf"] +
            ds_code_score * weights["ds_code"] +
            ds_quality * weights["ds_quality"] +
            code_quality * weights["code_quality"]
        )

        net_score = round(min(net_score, 1.0), 2)
        net_score_latency = self._ms(time.time() - t0)

        return{
            "net_score": net_score,
            "net_score_latency": net_score_latency
        }