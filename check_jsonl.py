import json
import argparse
from collections import defaultdict

def load_jsonl_objects(file_path, id_field='idx'):
    """
    加载JSONL文件中的对象，以id_field字段作为键
    """
    objects = {}
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                obj = json.loads(line.strip())
                obj_id = obj.get(id_field)
                if obj_id is None:
                    print(f"警告: 文件 {file_path} 第 {line_num} 行缺少 '{id_field}' 字段")
                    continue
                objects[obj_id] = obj
                count += 1
            except json.JSONDecodeError as e:
                print(f"错误: 文件 {file_path} 第 {line_num} 行JSON格式错误: {e}")
    
    return objects, count

def compare_objects(obj1, obj2, path=""):
    """
    递归比较两个对象，返回差异信息
    """
    differences = []
    
    # 如果两个都是字典，比较每个键
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        
        for key in all_keys:
            new_path = f"{path}.{key}" if path else key
            
            if key not in obj1:
                differences.append(f"字段缺失于第一个对象: {new_path}")
            elif key not in obj2:
                differences.append(f"字段缺失于第二个对象: {new_path}")
            else:
                differences.extend(compare_objects(obj1[key], obj2[key], new_path))
    
    # 如果两个都是列表，比较每个元素
    elif isinstance(obj1, list) and isinstance(obj2, list):
        if len(obj1) != len(obj2):
            differences.append(f"数组长度不同 {path}: {len(obj1)} vs {len(obj2)}")
        else:
            for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                differences.extend(compare_objects(item1, item2, f"{path}[{i}]"))
    
    # 其他类型的直接比较
    else:
        if obj1 != obj2:
            differences.append(f"值不同 {path}: {obj1} != {obj2}")
    
    return differences

def main():
    parser = argparse.ArgumentParser(description='比较两个JSONL文件的对象差异')
    parser.add_argument('file1', help='第一个JSONL文件路径')
    parser.add_argument('file2', help='第二个JSONL文件路径')
    parser.add_argument('--id-field', default='idx', help='对象唯一标识字段名，默认为"idx"')
    parser.add_argument('--output', help='输出差异结果到文件')
    
    args = parser.parse_args()
    
    print(f"正在加载文件 {args.file1}...")
    objects1, count1 = load_jsonl_objects(args.file1, args.id_field)
    
    print(f"正在加载文件 {args.file2}...")
    objects2, count2 = load_jsonl_objects(args.file2, args.id_field)
    
    print(f"\n统计结果:")
    print(f"文件 {args.file1} 中的对象数量: {count1}")
    print(f"文件 {args.file2} 中的对象数量: {count2}")
    
    # 找出只在第一个文件中的对象
    only_in_file1 = set(objects1.keys()) - set(objects2.keys())
    print(f"\n只在 {args.file1} 中的对象数量: {len(only_in_file1)}")
    
    # 找出只在第二个文件中的对象
    only_in_file2 = set(objects2.keys()) - set(objects1.keys())
    print(f"只在 {args.file2} 中的对象数量: {len(only_in_file2)}")
    
    # 找出两个文件都有的对象
    common_ids = set(objects1.keys()) & set(objects2.keys())
    print(f"两个文件共有的对象数量: {len(common_ids)}")
    
    # 比较共有对象的差异
    different_objects = []
    for obj_id in common_ids:
        differences = compare_objects(objects1[obj_id], objects2[obj_id])
        if differences:
            different_objects.append((obj_id, differences))
    
    print(f"共有对象中存在差异的数量: {len(different_objects)}")
    
    # 输出差异详情
    output_content = []
    if only_in_file1:
        output_content.append(f"只在 {args.file1} 中的对象ID:")
        output_content.extend([f"  {id}" for id in sorted(only_in_file1)])
        output_content.append("")
    
    if only_in_file2:
        output_content.append(f"只在 {args.file2} 中的对象ID:")
        output_content.extend([f"  {id}" for id in sorted(only_in_file2)])
        output_content.append("")
    
    if different_objects:
        output_content.append("共有对象中的差异:")
        for obj_id, differences in different_objects:
            output_content.append(f"对象 {obj_id} 的差异:")
            for diff in differences:
                output_content.append(f"  {diff}")
            output_content.append("")
    
    # 输出到屏幕或文件
    output_text = "\n".join(output_content)
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"\n差异详情已保存到: {args.output}")
    else:
        if output_text:
            print("\n" + output_text)
        else:
            print("\n两个文件内容完全相同!")

if __name__ == "__main__":
    main()