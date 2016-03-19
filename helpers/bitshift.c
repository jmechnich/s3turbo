/*
  https://unix.stackexchange.com/questions/55781/bit-shifting-a-file
*/

#include <stdio.h>
#include <stdlib.h>

#define SIZE (1024*1024)

int main (int argc, char *argv[])
{
  FILE *from = fopen(argv[1], "rb");
  FILE *to = fopen(argv[2], "wb");
  int nbits = atoi(argv[3]);
  int offs_bytes = nbits/8;
  int shift_bits = nbits%8;
  unsigned char *buf = malloc(SIZE);
  size_t res, pos, i;

  for (pos=0; pos<offs_bytes; pos++)
    buf[pos] = 0;

  buf[pos++] = 0;

  while ((res = fread(buf+pos, 1, SIZE-pos, from))) {
    for (i=0; i < res; i++) {
      buf[pos-1] |= (buf[pos] >> shift_bits) & 0xFF;
      buf[pos] = buf[pos] << (8 - shift_bits);
      pos++;
    }
    fwrite(buf, 1, pos-1, to);
    buf[0] = buf[pos-1];
    pos = 1;
  }
  fwrite(buf, 1, 1, to);
  fclose(from); fclose(to);
  return 0;
}
