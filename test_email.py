#!/usr/bin/env python3
"""测试邮件发送功能"""

import yaml
from email_sender import EmailSender

def test_email():
    # 加载配置
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    email_config = config.get('email', {})
    
    if not email_config.get('enabled'):
        print("邮件功能未启用")
        return
    
    print("=" * 50)
    print("测试邮件发送功能")
    print("=" * 50)
    print(f"发件人: {email_config.get('sender_email')}")
    print(f"收件人: {email_config.get('receiver_emails')}")
    print("=" * 50)
    
    # 创建邮件发送器
    sender = EmailSender(email_config)
    
    # 测试连接
    result = sender.test_connection()
    
    if result:
        print("\n✅ 邮件配置正确，可以发送邮件！")
    else:
        print("\n❌ 邮件配置有问题，请检查！")

if __name__ == "__main__":
    test_email()
