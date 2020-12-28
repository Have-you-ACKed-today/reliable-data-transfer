# Reliable Data Transfer
This is the final project of **CS305 Computer Network**

The task is to implement reliable data transfer on udp.

Happy coding and good luck!



## 1 Project Objective

Build our own **reliable data transfer** protocol dealing with packet loss, delay, data corruption and network congestion. Also, implement echo server demo basing on it. 



## 2 message header

### Header format:
```
------------------------------------------------------------------------
| reserved | SYN | FIN | ACK | SEQ | SEQACK | LEN | CHECKSUM | PAYLOAD |
------------------------------------------------------------------------
|    5b    | 1 b | 1 b | 1 b | 4 B |   4B   | 4 B |    1B    |  LEN B  |
------------------------------------------------------------------------
```



nqsnb mzynb lycnb
