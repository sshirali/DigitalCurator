"""Duplicate detection for Digital Curator MVP."""

from __future__ import annotations

from collections import defaultdict

import imagehash

from host.models import DuplicateGroup, FileRecord


class DuplicateDetector:
    def detect(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        """Group files by exact SHA-256 match, then by pHash Hamming distance ≤ 10."""
        groups: list[DuplicateGroup] = []
        ungrouped: list[FileRecord] = []

        # Step 1: Group by identical SHA-256 (exact duplicates)
        sha_buckets: dict[str, list[FileRecord]] = defaultdict(list)
        for record in records:
            sha_buckets[record.sha256].append(record)

        for sha, members in sha_buckets.items():
            if len(members) >= 2:
                winner = self._select_winner(members)
                groups.append(DuplicateGroup(
                    id=None,
                    group_type="exact",
                    members=list(members),
                    winner_id=winner.id,
                ))
            else:
                ungrouped.extend(members)

        # Step 2: Cluster remaining files by pHash Hamming distance ≤ 10 (near duplicates)
        near_groups = self._cluster_by_phash(ungrouped)
        groups.extend(near_groups)

        return groups

    def _cluster_by_phash(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        """Union-find clustering of records by pHash Hamming distance ≤ 10."""
        n = len(records)
        if n < 2:
            return []

        # Parse hashes once
        hashes = [imagehash.hex_to_hash(r.phash) for r in records]

        # Union-Find
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: int, y: int) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for i in range(n):
            for j in range(i + 1, n):
                if hashes[i] - hashes[j] <= 10:
                    union(i, j)

        # Collect clusters
        clusters: dict[int, list[FileRecord]] = defaultdict(list)
        for i, record in enumerate(records):
            clusters[find(i)].append(record)

        groups: list[DuplicateGroup] = []
        for members in clusters.values():
            if len(members) >= 2:
                winner = self._select_winner(members)
                groups.append(DuplicateGroup(
                    id=None,
                    group_type="near",
                    members=list(members),
                    winner_id=winner.id,
                ))

        return groups

    def _select_winner(self, group: list[FileRecord]) -> FileRecord:
        """Select the best file: largest file_size, tiebreak by highest laplacian_var."""
        return max(
            group,
            key=lambda r: (r.file_size, r.laplacian_var if r.laplacian_var is not None else 0.0),
        )
