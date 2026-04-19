export interface FileRecord {
  id: number;
  abs_path: string;
  thumb_path: string | null;
  file_size: number;
  last_modified: number;
  sha256: string;
  phash: string;
  thumb_status: string;
  is_screenshot: boolean;
  screenshot_conf: number;
  laplacian_var: number | null;
  mean_luminance: number | null;
  is_blurry: boolean;
  is_dark: boolean;
  decision: 'undecided' | 'keep' | 'delete';
  status: string;
}

export type Category = 'duplicates' | 'screenshots' | 'blurry';

export interface GroupMember {
  id: number;
  abs_path: string;
  thumb_path: string | null;
  width: number | null;
  height: number | null;
  laplacian_var: number | null;
  decision: 'undecided' | 'keep' | 'delete';
}

export interface DuplicateGroup {
  id: number;
  group_type: 'exact' | 'near';
  winner_id: number | null;
  members: GroupMember[];
}
