#!/usr/bin/env python3
"""
Temporal Bash History Analyzer - Identifies commands used across multiple non-adjacent days
to distinguish recurring workflows from temporary intensive tasks
"""

import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
import argparse
from datetime import datetime, timedelta


class TemporalAnalyzer:
    def __init__(self):
        self.commands = []
        self.all_commands = Counter()  # Unified tracking for all command patterns
        self.command_dates = defaultdict(set)  # command -> set of dates
        self.valid_commands = set()
        self.invalid_commands = set()
        self.skipped_count = 0
        self.skip_reasons = Counter()
        
    def parse_timestamp(self, line):
        """Extract timestamp from bash history line"""
        # Look for timestamp format: #1234567890
        timestamp_match = re.match(r'^#(\d+)', line.strip())
        if timestamp_match:
            timestamp = int(timestamp_match.group(1))
            return datetime.fromtimestamp(timestamp).date()
        return None
    

        
    def is_valid_command(self, cmd_word):
        """Check if a command word is a valid executable using 'type' command"""
        if cmd_word in self.valid_commands:
            return True
        if cmd_word in self.invalid_commands:
            return False
            
        try:
            result = subprocess.run(['type', cmd_word], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  universal_newlines=True, 
                                  shell=True)
            
            if result.returncode == 0:
                self.valid_commands.add(cmd_word)
                return True
            else:
                self.invalid_commands.add(cmd_word)
                return False
                
        except subprocess.SubprocessError:
            self.invalid_commands.add(cmd_word)
            return False
    
    def read_history(self):
        """Read bash history with timestamps"""
        history_entries = []
        history_file = Path.home() / ".bash_history"
        
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                current_date = None
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if this is a timestamp line
                    date = self.parse_timestamp(line)
                    if date:
                        current_date = date
                        continue
                    
                    # This is a command line
                    history_entries.append((line, current_date))
                
                print(f"Read {len(history_entries)} entries from {history_file}")
            except Exception as e:
                print(f"Error reading {history_file}: {e}")
        
        return history_entries
    
    def clean_command(self, command):
        """Clean and normalize a command"""
        command = command.strip()
        
        if not command or command.startswith('#'):
            return None
        return command
    
    def count_non_adjacent_days(self, dates):
        """Count non-adjacent days in a set of dates"""
        if not dates:
            return 0
            
        sorted_dates = sorted(dates)
        non_adjacent_count = 1  # First date is always non-adjacent
        
        for i in range(1, len(sorted_dates)):
            # If there's more than 1 day gap, it's non-adjacent
            if (sorted_dates[i] - sorted_dates[i-1]).days > 1:
                non_adjacent_count += 1
        
        return non_adjacent_count
    
    def analyze_commands(self, command_entries, min_non_adjacent_days=5):
        """Analyze commands with temporal filtering"""
        print("Analyzing commands with temporal filtering...")
        
        for i, (cmd, date) in enumerate(command_entries):
            if i % 1000 == 0:
                print(f"Processed {i}/{len(command_entries)} commands...")
                
            cleaned = self.clean_command(cmd)
            if not cleaned:
                continue
                
            parts = cleaned.split()
            if not parts:
                continue
            
            first_word = parts[0]
            
            if first_word in ['if', 'then', 'else', 'elif', 'fi', 'for', 'while', 'do', 'done', 'case', 'esac']:
                self.skipped_count += 1
                self.skip_reasons['shell_construct'] += 1
                continue
                
            if not self.is_valid_command(first_word):
                self.skipped_count += 1
                self.skip_reasons['invalid_command'] += 1
                continue
                
            if len(first_word) > 50:
                self.skipped_count += 1
                self.skip_reasons['too_long'] += 1
                continue
                
            # Track all patterns: full command, first word, and multi-word patterns
            patterns_to_track = [cleaned, first_word]  # Full command and root command
            
            # Add multi-word patterns (2-word, 3-word, etc.)
            for length in range(2, min(6, len(parts) + 1)):
                pattern = ' '.join(parts[:length])
                patterns_to_track.append(pattern)
            
            # Track dates and counts for all patterns
            for pattern in patterns_to_track:
                if date:
                    self.command_dates[pattern].add(date)
                self.all_commands[pattern] += 1
            
            # Keep original commands list for reference
            self.commands.append(cleaned)
        
        print(f"Initial filtering complete. Skipped {self.skipped_count} invalid commands.")
        
        # Now filter by temporal criteria
        print(f"Applying temporal filter: minimum {min_non_adjacent_days} non-adjacent days...")
        self.filter_by_temporal_usage(min_non_adjacent_days)
    
    def filter_by_temporal_usage(self, min_non_adjacent_days):
        """Filter commands by non-adjacent day usage"""
        # Filter all commands uniformly
        temporal_commands = Counter()
        for cmd, count in self.all_commands.items():
            non_adjacent_days = self.count_non_adjacent_days(self.command_dates[cmd])
            if non_adjacent_days >= min_non_adjacent_days:
                temporal_commands[cmd] = count
        
        # Calculate filtering statistics
        original_count = len(self.all_commands)
        filtered_count = original_count - len(temporal_commands)
        
        # Update to filtered commands
        self.all_commands = temporal_commands
        
        print(f"Temporal filtering removed {filtered_count} command patterns")
        print(f"(kept only commands used on {min_non_adjacent_days}+ non-adjacent days)")
    
    def analyze_root_commands(self):
        """Analyze commands by root to decide optimal aliasing strategy"""
        # Group commands by their root (first word)
        root_groups = defaultdict(list)
        
        for cmd, count in self.all_commands.items():
            if ' ' in cmd:  # Multi-word command
                root = cmd.split()[0]
                root_groups[root].append({
                    'command': cmd,
                    'count': count,
                    'savings_potential': (len(cmd) - 2) * count  # Assume 2-char alias
                })
        
        # Analyze each root group
        alias_recommendations = []
        
        for root, commands in root_groups.items():
            if not commands:
                continue
                
            # Calculate total usage of root vs individual patterns
            total_pattern_usage = sum(cmd['count'] for cmd in commands)
            root_usage = self.all_commands.get(root, 0)
            
            # Calculate potential savings for each approach
            # Option 1: Alias the root command
            if root_usage > 0:
                root_alias_savings = (len(root) - 1) * (root_usage + total_pattern_usage)
            else:
                root_alias_savings = 0
            
            # Option 2: Alias individual patterns
            pattern_alias_savings = sum(cmd['savings_potential'] for cmd in commands)
            
            # Decision logic
            if root_alias_savings > pattern_alias_savings * 1.2:  # 20% bonus for simplicity
                # Recommend aliasing the root
                if root_usage + total_pattern_usage >= 5:  # Minimum usage threshold
                    alias_recommendations.append({
                        'type': 'root',
                        'original': root,
                        'alias': root[0],  # Single letter alias
                        'count': root_usage + total_pattern_usage,
                        'savings': root_alias_savings,
                        'patterns': [cmd['command'] for cmd in commands]
                    })
            else:
                # Recommend individual pattern aliases
                for cmd in commands:
                    if cmd['count'] >= 3:  # Minimum usage threshold
                        alias_recommendations.append({
                            'type': 'pattern',
                            'original': cmd['command'],
                            'alias': self.generate_alias(cmd['command']),
                            'count': cmd['count'],
                            'savings': cmd['savings_potential'],
                            'patterns': [cmd['command']]
                        })
        
        return alias_recommendations
    
    def analyze_environment_variables(self):
        """Analyze commands for frequently used strings that could be environment variables"""
        # Extract any repeated string patterns from all commands
        string_usage = defaultdict(list)  # string -> list of (command, count) tuples
        
        for cmd, count in self.all_commands.items():
            # Look for various repeatable string patterns
            patterns_to_check = [
                # Git branch/remote patterns
                r'origin/[\w/.-]+',
                r'upstream/[\w/.-]+',
                # Paths (absolute and relative)
                r'/[\w/.-]{6,}',
                r'[\w.-]+/[\w/.-]{6,}',
                # URLs and network patterns
                r'https?://[\w/.-]+',
                r'[\w.-]+\.[\w.-]+/[\w/.-]+',
                r'[\w.-]+:\d+',  # host:port
                # File extensions and patterns
                r'--[\w-]+=[\w/.-]{4,}',  # --flag=value
                r'--[\w-]{4,}',  # --long-flag
                r'-[\w]{2,}',  # multi-char flags like -la, -rf
                # Version/hash patterns
                r'v\d+\.\d+[\w.-]*',  # version numbers
                r'[a-f0-9]{8,}',  # hex strings (commit hashes, etc.)
                # File patterns
                r'[\w.-]+\.[\w]{2,4}',  # file.extension
                # Command sequences
                r'[\w.-]{4,}',  # any word-like string 4+ chars
            ]
            
            for pattern in patterns_to_check:
                matches = re.findall(pattern, cmd)
                for match in matches:
                    # Filter criteria for environment variable candidates
                    if (len(match) >= 4 and  # Minimum length
                        not match.isdigit() and  # Not just a number
                        not re.match(r'^-[a-zA-Z]$', match) and  # Not single letter flags
                        not match in ['true', 'false', 'null', 'none'] and  # Not common values
                        len(set(match)) > 2):  # Has some variety in characters
                        string_usage[match].append((cmd, count))
        
        # Analyze string usage frequency
        env_var_candidates = []
        
        for string_pattern, usages in string_usage.items():
            # Calculate total usage across all commands
            total_usage = sum(count for _, count in usages)
            command_count = len(usages)
            
            # Adjust thresholds based on string type and length
            min_usage = max(5, 20 - len(string_pattern))  # Longer strings need fewer uses
            min_commands = 2 if len(string_pattern) > 10 else 3
            
            # Only suggest if used frequently enough
            if total_usage >= min_usage and command_count >= min_commands:
                # Generate environment variable name
                env_name = self.generate_env_var_name(string_pattern)
                
                # Calculate potential savings
                # Each usage saves (len(string) - len($ENV_NAME))
                var_ref_length = len(f"${env_name}")
                chars_saved_per_use = len(string_pattern) - var_ref_length
                
                if chars_saved_per_use > 0:
                    total_chars_saved = chars_saved_per_use * total_usage
                    
                    # Get temporal info for the string
                    all_dates = set()
                    for cmd, _ in usages:
                        all_dates.update(self.command_dates.get(cmd, set()))
                    
                    non_adjacent_days = self.count_non_adjacent_days(all_dates)
                    date_span = max(all_dates) - min(all_dates) if all_dates else timedelta(0)
                    
                    env_var_candidates.append({
                        'string': string_pattern,
                        'env_name': env_name,
                        'total_usage': total_usage,
                        'command_count': command_count,
                        'commands': [cmd for cmd, _ in usages],
                        'chars_per_use': chars_saved_per_use,
                        'total_chars_saved': total_chars_saved,
                        'non_adjacent_days': non_adjacent_days,
                        'date_span': date_span.days if all_dates else 0,
                        'string_type': self.classify_string_type(string_pattern)
                    })
        
        # Sort by total savings potential
        env_var_candidates.sort(key=lambda x: x['total_chars_saved'], reverse=True)
        
        return env_var_candidates
    
    def classify_string_type(self, string_pattern):
        """Classify the type of string for better categorization"""
        if re.match(r'^https?://', string_pattern):
            return 'URL'
        elif re.match(r'^/', string_pattern):
            return 'Path'
        elif re.match(r'[\w.-]+/[\w/.-]+', string_pattern):
            return 'Path/Branch'
        elif re.match(r'--[\w-]+', string_pattern):
            return 'Flag'
        elif re.match(r'[\w.-]+:\d+', string_pattern):
            return 'Host:Port'
        elif re.match(r'[a-f0-9]{8,}', string_pattern):
            return 'Hash'
        elif re.match(r'v\d+\.\d+', string_pattern):
            return 'Version'
        elif re.match(r'[\w.-]+\.[\w]{2,4}$', string_pattern):
            return 'File'
        else:
            return 'String'
    
    def generate_env_var_name(self, string_pattern):
        """Generate a meaningful environment variable name for any string pattern"""
        clean_string = string_pattern
        
        # Handle different string types
        if re.match(r'^https?://', string_pattern):
            # URL handling
            clean_string = re.sub(r'^https?://', '', clean_string)
            clean_string = re.sub(r'/.*$', '', clean_string)  # Keep just hostname
            prefix = "URL"
        elif re.match(r'^--[\w-]+', string_pattern):
            # Flag handling
            clean_string = re.sub(r'^--', '', string_pattern)
            prefix = "FLAG"
        elif re.match(r'^origin/', string_pattern):
            # Git branch/remote
            clean_string = re.sub(r'^origin/', '', string_pattern)
            prefix = "BRANCH"
        elif re.match(r'^/', string_pattern):
            # Absolute path
            clean_string = re.sub(r'^/proj_risc/user_dev/[\w]+/', '', clean_string)
            clean_string = re.sub(r'^/home/[\w]+/', '', clean_string)
            clean_string = re.sub(r'^/', '', clean_string)
            prefix = ""
        elif re.match(r'[\w.-]+:\d+', string_pattern):
            # Host:port
            clean_string = re.sub(r':\d+$', '', string_pattern)
            prefix = "HOST"
        elif re.match(r'[a-f0-9]{8,}', string_pattern):
            # Hash/commit
            return "COMMIT_HASH"
        elif re.match(r'v\d+\.\d+', string_pattern):
            # Version
            return "VERSION"
        else:
            prefix = ""
        
        # Split into meaningful parts
        parts = re.split(r'[/._-]', clean_string)
        
        # Filter meaningful parts (not empty, not single chars, not numbers only)
        meaningful_parts = [p for p in parts if len(p) > 1 and not p.isdigit()]
        
        if not meaningful_parts:
            # Fallback - use original string parts
            parts = string_pattern.split('/')
            meaningful_parts = [p for p in parts if len(p) > 1][-2:]
        
        # Create env var name from parts
        if len(meaningful_parts) >= 2:
            base_name = '_'.join(meaningful_parts[:2])
        elif meaningful_parts:
            base_name = meaningful_parts[0]
        else:
            base_name = "VAR"
        
        # Combine prefix and base name
        if prefix:
            env_name = f"{prefix}_{base_name}".upper()
        else:
            env_name = base_name.upper()
        
        # Clean up the name
        env_name = re.sub(r'[^A-Z0-9_]', '_', env_name)
        env_name = re.sub(r'_+', '_', env_name)
        env_name = env_name.strip('_')
        
        # Ensure it's not too long
        if len(env_name) > 20:
            env_name = env_name[:20]
        
        return env_name
    
    def generate_alias(self, command):
        """Generate a short alias for a command"""
        parts = command.split()
        
        if len(parts) == 2:
            return parts[0][0] + parts[1][0]
        elif parts[0] in ['git', 'g', 'docker', 'npm', 'pip']:
            return parts[0][0] + ''.join(p[0] for p in parts[1:3])
        else:
            return ''.join(p[0] for p in parts[:3])
    
    def calculate_temporal_savings(self):
        """Calculate savings for temporally recurring commands using smart alias logic"""
        print("=" * 80)
        print("TEMPORAL SAVINGS ANALYSIS (Smart Aliasing & Environment Variables)")
        print("=" * 80)
        
        # Get smart alias recommendations
        alias_recommendations = self.analyze_root_commands()
        
        # Get environment variable recommendations
        env_var_recommendations = self.analyze_environment_variables()
        
        # Sort by savings potential
        alias_recommendations.sort(key=lambda x: x['savings'], reverse=True)
        
        total_chars_saved = 0
        total_commands_affected = 0
        savings_data = []
        
        for rec in alias_recommendations[:25]:  # Top 25 recommendations
            cmd = rec['original']
            alias_name = rec['alias']
            count = rec['count']
            
            # Calculate actual savings
            original_length = len(cmd)
            alias_length = len(alias_name)
            chars_saved_per_use = original_length - alias_length
            total_chars_saved_cmd = chars_saved_per_use * count
            
            # Get temporal info
            dates = self.command_dates[cmd]
            non_adjacent_days = self.count_non_adjacent_days(dates)
            date_span = max(dates) - min(dates) if dates else timedelta(0)
            
            if chars_saved_per_use > 0:
                total_chars_saved += total_chars_saved_cmd
                total_commands_affected += count
                
                savings_data.append({
                    'original': cmd,
                    'alias': alias_name,
                    'count': count,
                    'chars_per_use': chars_saved_per_use,
                    'total_chars': total_chars_saved_cmd,
                    'non_adjacent_days': non_adjacent_days,
                    'date_span': date_span.days,
                    'type': rec['type']
                })
        
        # Sort by total character savings
        savings_data.sort(key=lambda x: x['total_chars'], reverse=True)
        
        print(f"SMART ALIAS SUGGESTIONS (Root vs Pattern Analysis):")
        print("-" * 95)
        print(f"{'Rank':<4} {'Original Command':<30} {'Alias':<8} {'Type':<8} {'Uses':<6} {'Days':<6} {'Span':<8} {'Savings':<15}")
        print("-" * 95)
        
        for i, data in enumerate(savings_data[:20], 1):
            alias_type = data.get('type', 'pattern')[:7]  # Truncate to fit
            print(f"{i:3d}. {data['original']:<30} {data['alias']:<8} "
                  f"{alias_type:<8} {data['count']:4d}x  {data['non_adjacent_days']:4d}d  {data['date_span']:6d}d  "
                  f"{data['chars_per_use']:2d}×{data['count']} = {data['total_chars']:4d} chars")
        
        # Display environment variable suggestions
        print(f"\nENVIRONMENT VARIABLE SUGGESTIONS (Frequent Strings):")
        print("-" * 105)
        print(f"{'Rank':<4} {'String':<35} {'Type':<8} {'Env Var':<15} {'Uses':<6} {'Cmds':<5} {'Days':<6} {'Savings':<15}")
        print("-" * 105)
        
        env_total_chars_saved = 0
        env_total_usage = 0
        
        for i, env_data in enumerate(env_var_recommendations[:15], 1):
            env_total_chars_saved += env_data['total_chars_saved']
            env_total_usage += env_data['total_usage']
            
            string_type = env_data.get('string_type', 'String')[:7]  # Truncate to fit
            print(f"{i:3d}. {env_data['string']:<35} {string_type:<8} ${env_data['env_name']:<14} "
                  f"{env_data['total_usage']:4d}x  {env_data['command_count']:3d}   {env_data['non_adjacent_days']:4d}d  "
                  f"{env_data['chars_per_use']:2d}×{env_data['total_usage']} = {env_data['total_chars_saved']:4d} chars")
        
        if env_var_recommendations:
            print(f"\nExample usage for top suggestion:")
            top_env = env_var_recommendations[0]
            print(f"  export {top_env['env_name']}=\"{top_env['string']}\"")
            if top_env['commands']:
                example_cmd = top_env['commands'][0]
                replaced_cmd = example_cmd.replace(top_env['string'], f"${top_env['env_name']}")
                print(f"  Before: {example_cmd}")
                print(f"  After:  {replaced_cmd}")
        
        # Update total savings to include environment variables
        total_chars_saved += env_total_chars_saved
        total_commands_affected += env_total_usage
        
        print(f"\nCOMBINED SAVINGS SUMMARY:")
        print(f"- Alias savings: {total_chars_saved - env_total_chars_saved:,} chars")
        print(f"- Environment variable savings: {env_total_chars_saved:,} chars")
        print(f"- TOTAL characters saved: {total_chars_saved:,} chars")
        print(f"- Commands/usages affected: {total_commands_affected:,}")
        print(f"- Recurring commands analyzed: {len(self.commands):,}")
        print(f"- One-off commands filtered: {self.skipped_count:,}")
        
        if total_commands_affected > 0:
            print(f"- Average savings per usage: {total_chars_saved/total_commands_affected:.1f} characters")
            time_saved_minutes = total_chars_saved / 200
            print(f"- Estimated time saved: {time_saved_minutes:.1f} minutes")
        print()
        
        return savings_data
    
    def show_temporal_summary(self):
        """Show temporal filtering summary"""
        print("TEMPORAL FILTERING SUMMARY:")
        print("-" * 45)
        
        total_processed = len(self.commands) + self.skipped_count
        print(f"Total entries processed: {total_processed:,}")
        print(f"Commands with sufficient temporal recurrence: {len(self.commands):,}")
        print(f"One-off/temporary patterns filtered: {self.skipped_count:,}")
        print()
        
        print("Filtering breakdown:")
        for reason, count in self.skip_reasons.most_common():
            print(f"  - {reason.replace('_', ' ').title()}: {count:,}")
        print()
        
        # Show date range of analysis
        all_dates = set()
        for dates in self.command_dates.values():
            all_dates.update(dates)
        
        if all_dates:
            min_date = min(all_dates)
            max_date = max(all_dates)
            span = (max_date - min_date).days
            print(f"Analysis period: {min_date} to {max_date} ({span} days)")
        print()
    
    def show_top_recurring_commands(self):
        """Show top recurring single-word commands with temporal info"""
        print("TOP 15 RECURRING COMMANDS (Multi-Day Usage):")
        print("-" * 60)
        print(f"{'Rank':<4} {'Command':<20} {'Uses':<6} {'Days':<6} {'Span':<8}")
        print("-" * 60)
        
        # Filter to single-word commands only for this display
        single_word_commands = {cmd: count for cmd, count in self.all_commands.items() 
                               if ' ' not in cmd}
        
        total_commands = len(self.commands)
        for i, (cmd, count) in enumerate(Counter(single_word_commands).most_common(15), 1):
            dates = self.command_dates[cmd]
            non_adjacent_days = self.count_non_adjacent_days(dates)
            date_span = (max(dates) - min(dates)).days if dates else 0
            percentage = (count / total_commands) * 100
            
            print(f"{i:2d}. {cmd:<20} {count:4d}x  {non_adjacent_days:4d}d  {date_span:6d}d ({percentage:4.1f}%)")
        print()
    
    def generate_executive_summary(self, min_non_adjacent_days):
        """Generate executive summary"""
        total_commands = len(self.commands)
        unique_commands = len(set(self.commands))
        total_processed = total_commands + self.skipped_count
        
        print("=" * 80)
        print("TEMPORAL ANALYSIS EXECUTIVE SUMMARY")
        print("=" * 80)
        print(f"Total entries processed: {total_processed:,}")
        print(f"Recurring commands (used on {min_non_adjacent_days}+ non-adjacent days): {total_commands:,}")
        print(f"Temporary/one-off patterns filtered: {self.skipped_count:,}")
        print(f"Unique recurring commands: {unique_commands:,}")
        print(f"Command repetition rate: {((total_commands - unique_commands) / total_commands * 100):.1f}%")
        print(f"Temporal filter effectiveness: {(self.skipped_count / total_processed * 100):.1f}% noise removed")
        print()
        
        print("TOP OPTIMIZATION OPPORTUNITIES:")
        print("1. Create aliases for frequently used recurring multi-word commands")
        print("2. Focus on commands with consistent multi-day usage patterns")
        print("3. Prioritize git workflow optimizations (if they recur)")
        print("4. Ignore temporary project-specific intensive work")
        print()


def main():
    parser = argparse.ArgumentParser(description='Temporal bash history analysis focusing on recurring patterns')
    parser.add_argument('--min-days', type=int, default=5, 
                       help='Minimum non-adjacent days for inclusion (default: 5)')
    parser.add_argument('--min-count', type=int, default=3,
                       help='Minimum usage count (default: 3)')
    
    args = parser.parse_args()
    
    analyzer = TemporalAnalyzer()
    
    print("Performing temporal bash history analysis...")
    print(f"Filtering for commands used on at least {args.min_days} non-adjacent days")
    
    command_entries = analyzer.read_history()
    
    if not command_entries:
        print("No history entries found.")
        return
    
    analyzer.analyze_commands(command_entries, args.min_days)
    
    # Generate all analyses
    analyzer.generate_executive_summary(args.min_days)
    analyzer.show_temporal_summary()
    analyzer.show_top_recurring_commands()
    analyzer.calculate_temporal_savings()


if __name__ == "__main__":
    main() 