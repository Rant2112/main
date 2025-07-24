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
        print("TEMPORAL SAVINGS ANALYSIS (Smart Aliasing)")
        print("=" * 80)
        
        # Get smart alias recommendations
        alias_recommendations = self.analyze_root_commands()
        
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
                    'type': rec['type'],
                        'chars_per_use': chars_saved_per_use,
                        'total_chars': total_chars_saved_cmd,
                        'non_adjacent_days': non_adjacent_days,
                        'date_span': date_span.days,
                        'type': 'alias'
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
        
        print(f"\nTEMPORAL SAVINGS SUMMARY:")
        print(f"- Recurring commands analyzed: {len(self.commands):,}")
        print(f"- One-off commands filtered: {self.skipped_count:,}")
        print(f"- Characters saved: {total_chars_saved:,}")
        print(f"- Commands affected: {total_commands_affected:,}")
        
        if total_commands_affected > 0:
            print(f"- Average savings per command: {total_chars_saved/total_commands_affected:.1f} characters")
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