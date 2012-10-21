def morgue_timestring(time):
  return "%04d%02d%02d-%02d%02d%02d" % (time.year, time.month, time.day,
                                        time.hour, time.minute, time.second)
