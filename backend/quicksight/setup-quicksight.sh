#!/bin/bash

# QuickSight Setup Script for Sales Data Platform
# This script helps set up QuickSight resources that require API calls
# before Terraform can create the data sources and datasets.

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
QUICKSIGHT_EDITION="${QUICKSIGHT_EDITION:-ENTERPRISE}"

# Check for required notification email
if [ -z "$NOTIFICATION_EMAIL" ]; then
    echo "Error: NOTIFICATION_EMAIL environment variable is required."
    echo "Usage: NOTIFICATION_EMAIL=your@email.com ./setup-quicksight.sh"
    exit 1
fi

echo "=============================================="
echo "QuickSight Setup for Sales Data Platform"
echo "=============================================="
echo "AWS Account: $ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Edition: $QUICKSIGHT_EDITION"
echo ""

# Function to check if QuickSight is already set up
check_quicksight_subscription() {
    echo "Checking QuickSight subscription status..."
    if aws quicksight describe-account-subscription --aws-account-id "$ACCOUNT_ID" 2>/dev/null; then
        echo "QuickSight subscription exists."
        return 0
    else
        echo "QuickSight subscription not found."
        return 1
    fi
}

# Function to create QuickSight subscription
create_quicksight_subscription() {
    echo ""
    echo "Creating QuickSight subscription..."
    echo "Note: This creates an Enterprise subscription which has costs associated."
    read -p "Continue? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "Aborted."
        exit 1
    fi

    aws quicksight create-account-subscription \
        --aws-account-id "$ACCOUNT_ID" \
        --edition "$QUICKSIGHT_EDITION" \
        --authentication-method IAM_AND_QUICKSIGHT \
        --account-name "SalesDataPlatform" \
        --notification-email "$NOTIFICATION_EMAIL" \
        --region "$AWS_REGION"

    echo "QuickSight subscription created. Please wait 2-3 minutes for it to be active."
    echo "You may need to complete setup in the AWS Console."
}

# Function to register QuickSight user
register_quicksight_user() {
    local email="$1"
    local username="$2"
    local role="${3:-ADMIN}"

    echo ""
    echo "Registering QuickSight user: $username ($email)..."

    aws quicksight register-user \
        --aws-account-id "$ACCOUNT_ID" \
        --namespace default \
        --email "$email" \
        --identity-type IAM \
        --user-role "$role" \
        --iam-arn "arn:aws:iam::$ACCOUNT_ID:user/$username" \
        --region "$AWS_REGION" || echo "User may already exist"
}

# Function to list QuickSight users
list_quicksight_users() {
    echo ""
    echo "QuickSight Users:"
    aws quicksight list-users \
        --aws-account-id "$ACCOUNT_ID" \
        --namespace default \
        --region "$AWS_REGION" \
        --query 'UserList[].{UserName:UserName,Email:Email,Role:Role,Arn:Arn}' \
        --output table 2>/dev/null || echo "No users found or QuickSight not set up"
}

# Function to get QuickSight user ARN
get_quicksight_user_arn() {
    local username="$1"
    aws quicksight describe-user \
        --aws-account-id "$ACCOUNT_ID" \
        --namespace default \
        --user-name "$username" \
        --region "$AWS_REGION" \
        --query 'User.Arn' \
        --output text 2>/dev/null
}

# Function to create QuickSight group
create_quicksight_group() {
    local group_name="${1:-SalesDataPlatformUsers}"
    echo ""
    echo "Creating QuickSight group: $group_name..."

    aws quicksight create-group \
        --aws-account-id "$ACCOUNT_ID" \
        --namespace default \
        --group-name "$group_name" \
        --description "Users with access to Sales Data Platform dashboards" \
        --region "$AWS_REGION" || echo "Group may already exist"
}

# Function to add user to group
add_user_to_group() {
    local username="$1"
    local group_name="${2:-SalesDataPlatformUsers}"

    echo "Adding $username to group $group_name..."
    aws quicksight create-group-membership \
        --aws-account-id "$ACCOUNT_ID" \
        --namespace default \
        --group-name "$group_name" \
        --member-name "$username" \
        --region "$AWS_REGION" || echo "User may already be in group"
}

# Function to display next steps
show_next_steps() {
    echo ""
    echo "=============================================="
    echo "Next Steps"
    echo "=============================================="
    echo ""
    echo "1. Get your QuickSight user ARN:"
    echo "   aws quicksight list-users --aws-account-id $ACCOUNT_ID --namespace default"
    echo ""
    echo "2. Update your terraform.tfvars:"
    echo "   enable_quicksight = true"
    echo "   quicksight_user_arn = \"<YOUR_QUICKSIGHT_USER_ARN>\""
    echo ""
    echo "3. Run Terraform:"
    echo "   terraform plan"
    echo "   terraform apply"
    echo ""
    echo "4. Generate sample data by uploading store files to trigger the pipeline."
    echo ""
    echo "5. Access your dashboard at:"
    echo "   https://$AWS_REGION.quicksight.aws.amazon.com/"
    echo ""
}

# Main script
main() {
    case "${1:-help}" in
        check)
            check_quicksight_subscription
            list_quicksight_users
            ;;
        setup)
            if ! check_quicksight_subscription; then
                create_quicksight_subscription
            fi
            create_quicksight_group
            list_quicksight_users
            show_next_steps
            ;;
        register-user)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo "Usage: $0 register-user <email> <iam-username> [role]"
                echo "Roles: ADMIN, AUTHOR, READER"
                exit 1
            fi
            register_quicksight_user "$2" "$3" "${4:-AUTHOR}"
            ;;
        list-users)
            list_quicksight_users
            ;;
        get-user-arn)
            if [ -z "$2" ]; then
                echo "Usage: $0 get-user-arn <username>"
                exit 1
            fi
            get_quicksight_user_arn "$2"
            ;;
        help|*)
            echo "Usage: $0 <command>"
            echo ""
            echo "Commands:"
            echo "  check         - Check QuickSight subscription status"
            echo "  setup         - Set up QuickSight subscription and group"
            echo "  register-user - Register an IAM user in QuickSight"
            echo "  list-users    - List QuickSight users"
            echo "  get-user-arn  - Get ARN for a QuickSight user"
            echo "  help          - Show this help"
            echo ""
            echo "Environment variables:"
            echo "  AWS_REGION          - AWS region (default: us-east-1)"
            echo "  NOTIFICATION_EMAIL  - Email for QuickSight notifications"
            echo "  QUICKSIGHT_EDITION  - STANDARD or ENTERPRISE (default: ENTERPRISE)"
            ;;
    esac
}

main "$@"
