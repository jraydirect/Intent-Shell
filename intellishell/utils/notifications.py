"""Windows native notification support."""

import logging

logger = logging.getLogger(__name__)


def send_notification(title: str, message: str, duration: int = 5) -> bool:
    """
    Send a Windows native toast notification.
    
    Args:
        title: Notification title
        message: Notification message
        duration: Duration in seconds (default: 5)
        
    Returns:
        True if notification sent successfully, False otherwise
    """
    # Try plyer first (cross-platform)
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="IntelliShell",
            timeout=duration
        )
        logger.debug(f"Notification sent via plyer: {title}")
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"plyer notification failed: {e}")
    
    # Try win10toast (Windows-specific)
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        toaster.show_toast(
            title,
            message,
            duration=duration,
            threaded=True
        )
        logger.debug(f"Notification sent via win10toast: {title}")
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"win10toast notification failed: {e}")
    
    # Try windows-toasts (modern Windows)
    try:
        from windows_toasts import Toast, WindowsToaster
        toaster = WindowsToaster("IntelliShell")
        newToast = Toast()
        newToast.text_fields = [title, message]
        toaster.show_toast(newToast)
        logger.debug(f"Notification sent via windows-toasts: {title}")
        return True
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"windows-toasts notification failed: {e}")
    
    # Fallback: log warning
    logger.warning(
        f"No notification library available. "
        f"Install plyer or win10toast: pip install plyer win10toast"
    )
    logger.info(f"Notification (not sent): {title} - {message}")
    return False


def check_notification_support() -> tuple[bool, str]:
    """
    Check if notification support is available.
    
    Returns:
        Tuple of (is_supported, library_name)
    """
    try:
        from plyer import notification
        return True, "plyer"
    except ImportError:
        pass
    
    try:
        from win10toast import ToastNotifier
        return True, "win10toast"
    except ImportError:
        pass
    
    try:
        from windows_toasts import WindowsToaster
        return True, "windows-toasts"
    except ImportError:
        pass
    
    return False, "none"
