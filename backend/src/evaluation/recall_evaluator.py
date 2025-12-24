import logging
from typing import Dict, List, Set
from collections import defaultdict

from evaluation.recall_metrics import recall_at_k, hitrate_at_k
from evaluation.bucket_utils import item_popularity_buckets

logger = logging.getLogger(__name__)


class RecallEvaluator:
    def __init__(
        self,
        retrievers: Dict[str, callable],
        k_values: List[int],
        item_interaction_counts: Dict[int, int],
        total_items: int
    ) -> None:
        self.retrievers = retrievers
        self.k_values = k_values
        self.total_items = total_items
        self.item_buckets = item_popularity_buckets(item_interaction_counts)

    def evaluate_user(
        self,
        user_id: int,
        ground_truth_items: Set[int]
    ) -> Dict[str, Dict[str, float]]:
        results = defaultdict(dict)

        retrieved_by_model: Dict[str, List[int]] = {}
        union_items: List[int] = []

        for name, retriever in self.retrievers.items():
            items = retriever(user_id)
            retrieved_by_model[name] = items
            union_items.extend(items)

        union_items = list(dict.fromkeys(union_items))

        for model_name, items in retrieved_by_model.items():
            for k in self.k_values:
                results[model_name][f"recall@{k}"] = recall_at_k(
                    ground_truth_items, items, k
                )
                results[model_name][f"hitrate@{k}"] = hitrate_at_k(
                    ground_truth_items, items, k
                )

        for k in self.k_values:
            results["union"][f"recall@{k}"] = recall_at_k(
                ground_truth_items, union_items, k
            )
            results["union"][f"hitrate@{k}"] = hitrate_at_k(
                ground_truth_items, union_items, k
            )

        return results

    def evaluate(
        self,
        eval_users: Dict[int, Set[int]]
    ) -> Dict[str, Dict[str, float]]:
        aggregate = defaultdict(lambda: defaultdict(list))

        for user_id, gt_items in eval_users.items():
            user_results = self.evaluate_user(user_id, gt_items)
            for model, metrics in user_results.items():
                for metric, value in metrics.items():
                    aggregate[model][metric].append(value)

        return {
            model: {
                metric: float(sum(values) / max(len(values), 1))
                for metric, values in metrics.items()
            }
            for model, metrics in aggregate.items()
        }
