#!/usr/bin/env python3
"""
@summary: An atomic, thread-safe incrementing nonce. To deal with transaction on same account
"""
from threading import Lock


class AtomicNonce:
    """An atomic, thread-safe incrementing nonce.
    >>> nonce = AtomicNonce()
    >>> nonce.increment()
    1
    >>> nonce.increment(4)
    5
    >>> nonce = AtomicNonce(42.5)
    >>> nonce.value
    42.5
    >>> nonce.increment(0.5)
    43.0
    >>> nonce = AtomicNonce()
    >>> def incrementor():
    ...     for i in range(100000):
    ...         nonce.increment()
    >>> threads = []
    >>> for i in range(4):
    ...     thread = threading.Thread(target=incrementor)
    ...     thread.start()
    ...     threads.append(thread)
    >>> for thread in threads:
    ...     thread.join()
    >>> nonce.value
    400000
    """

    def __init__(self, w3, address):
        """Initialize a new atomic nonce to given initial value"""
        self.address = address
        self.value = w3.eth.getTransactionCount(self.address) - 1
        self._lock = Lock()

    def increment(self, w3, num=1):
        """Atomically increment the nonce by num (default 1) and return the
        new value.
        """
        with self._lock:
            self.value = self.value + num
            return self.value
